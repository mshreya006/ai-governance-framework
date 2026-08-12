import json
import os
import threading
import logging
import boto3
from botocore.exceptions import ClientError
from backend.app import config

from decimal import Decimal

logger = logging.getLogger(__name__)

def convert_floats_to_decimal(obj):
    """Recursively convert float to Decimal for DynamoDB write compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    return obj

def convert_decimals_to_float(obj):
    """Recursively convert Decimal back to float/int for application & JSON compatibility."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals_to_float(v) for v in obj]
    return obj

class DatabaseClient:
    """
    A unified Database Client that wraps DynamoDB on AWS and
    falls back to a local JSON file database for offline/local execution.
    """
    def __init__(self):
        self.use_dynamodb = False
        self.db_lock = threading.Lock()
        self.table = None

        # Check if AWS credentials are set or if we are in Lambda
        # We try to initialize boto3 client
        if not config.IS_LOCAL or (
            os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY")
        ):
            try:
                self.dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)
                self.table = self.dynamodb.Table(config.DYNAMODB_TABLE)
                # Test connection / table existence
                self.table.load()
                self.use_dynamodb = True
                logger.info(f"Connected to AWS DynamoDB Table: {config.DYNAMODB_TABLE}")
            except ClientError as e:
                logger.warning(
                    f"AWS DynamoDB table '{config.DYNAMODB_TABLE}' not reachable. "
                    f"Error: {e}. Falling back to local JSON database."
                )
            except Exception as e:
                logger.warning(
                    f"Failed to connect to AWS. Error: {e}. "
                    "Falling back to local JSON database."
                )
        else:
            logger.info("Local environment detected. Using local JSON database.")

        if not self.use_dynamodb:
            # Local JSON database file initialization
            self.local_db_path = config.LOCAL_DB_PATH
            with self.db_lock:
                if not os.path.exists(self.local_db_path):
                    with open(self.local_db_path, "w") as f:
                        json.dump({}, f)

    def _read_local_db(self) -> dict:
        try:
            with open(self.local_db_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_local_db(self, data: dict):
        with open(self.local_db_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_item(self, pk: str, sk: str) -> dict | None:
        """Retrieve a single item from the database by PK and SK."""
        if self.use_dynamodb:
            try:
                response = self.table.get_item(Key={"PK": pk, "SK": sk})
                item = response.get("Item")
                return convert_decimals_to_float(item) if item else None
            except ClientError as e:
                logger.error(f"DynamoDB GetItem Error: {e}")
                return None
        else:
            with self.db_lock:
                db_data = self._read_local_db()
                return db_data.get(pk, {}).get(sk)

    def put_item(self, pk: str, sk: str, item: dict):
        """Insert or overwrite an item in the database with PK and SK."""
        item_copy = dict(item)
        item_copy["PK"] = pk
        item_copy["SK"] = sk

        if self.use_dynamodb:
            try:
                dynamodb_item = convert_floats_to_decimal(item_copy)
                self.table.put_item(Item=dynamodb_item)
            except ClientError as e:
                logger.error(f"DynamoDB PutItem Error: {e}")
                raise e
        else:
            with self.db_lock:
                db_data = self._read_local_db()
                if pk not in db_data:
                    db_data[pk] = {}
                db_data[pk][sk] = item_copy
                self._write_local_db(db_data)

    def query_items(self, pk: str, sk_prefix: str = None) -> list[dict]:
        """Query items by PK and optionally an SK prefix."""
        if self.use_dynamodb:
            try:
                if sk_prefix:
                    key_condition = boto3.dynamodb.conditions.Key("PK").eq(pk) & boto3.dynamodb.conditions.Key("SK").begins_with(sk_prefix)
                else:
                    key_condition = boto3.dynamodb.conditions.Key("PK").eq(pk)
                
                response = self.table.query(KeyConditionExpression=key_condition)
                items = response.get("Items", [])
                return [convert_decimals_to_float(item) for item in items]
            except ClientError as e:
                logger.error(f"DynamoDB Query Error: {e}")
                return []
        else:
            with self.db_lock:
                db_data = self._read_local_db()
                pk_group = db_data.get(pk, {})
                items = []
                for sk, item in pk_group.items():
                    if not sk_prefix or sk.startswith(sk_prefix):
                        items.append(item)
                # Sort items by SK to simulate DynamoDB's range-key sorting
                items.sort(key=lambda x: x.get("SK", ""))
                return items

    def delete_item(self, pk: str, sk: str):
        """Remove an item from the database by PK and SK."""
        if self.use_dynamodb:
            try:
                self.table.delete_item(Key={"PK": pk, "SK": sk})
            except ClientError as e:
                logger.error(f"DynamoDB DeleteItem Error: {e}")
                raise e
        else:
            with self.db_lock:
                db_data = self._read_local_db()
                if pk in db_data and sk in db_data[pk]:
                    del db_data[pk][sk]
                    # Clean up PK group if empty
                    if not db_data[pk]:
                        del db_data[pk]
                    self._write_local_db(db_data)

# Singleton Instance
db = DatabaseClient()
