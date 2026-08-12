# deploy_frontend.ps1
# Prompt for unique bucket name
$bucketName = Read-Host -Prompt "Enter a unique S3 bucket name for your dashboard (e.g., ai-gov-dashboard-shreya-99)"
$region = "ap-south-1"

if ([string]::IsNullOrWhiteSpace($bucketName)) {
    Write-Error "Bucket name cannot be empty."
    exit
}

Write-Host "1. Building frontend production assets..." -ForegroundColor Cyan
cd frontend
npm run build
cd ..

Write-Host "`n2. Creating S3 bucket: $bucketName in $region..." -ForegroundColor Cyan
aws s3api create-bucket --bucket $bucketName --region $region --create-bucket-configuration LocationConstraint=$region

Write-Host "`n3. Disabling S3 Block Public Access..." -ForegroundColor Cyan
aws s3api delete-public-access-block --bucket $bucketName --region $region

Write-Host "`n4. Creating and applying public read bucket policy..." -ForegroundColor Cyan
$policy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$bucketName/*"
        }
    ]
}
"@
$policy | Out-File -FilePath s3_policy.json -Encoding ascii
aws s3api put-bucket-policy --bucket $bucketName --policy file://s3_policy.json
Remove-Item s3_policy.json -Force

Write-Host "`n5. Enabling Static Website Hosting..." -ForegroundColor Cyan
aws s3api put-bucket-website --bucket $bucketName --website-configuration "{\`"IndexDocument\`":{\`"Suffix\`":\`"index.html\`"},\`"ErrorDocument\`":{\`"Key\`":\`"index.html\`"}}"

Write-Host "`n6. Syncing frontend/dist files to S3..." -ForegroundColor Cyan
aws s3 sync frontend/dist s3://$bucketName

Write-Host "`n====================================================================" -ForegroundColor Green
Write-Host "SUCCESS! Your Frontend Control Center is deployed to AWS S3." -ForegroundColor Green
Write-Host "Access it here:" -ForegroundColor Green
Write-Host "http://$bucketName.s3-website.$region.amazonaws.com" -ForegroundColor Yellow
Write-Host "====================================================================" -ForegroundColor Green
