<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>Human-in-the-Loop Approvals</h1>
        <p class="subtitle" style="margin-bottom: 0;">Operational queue holding high-risk AI workloads paused by active policy rules. Review context parameters before approval decisions.</p>
      </div>
      <button class="btn btn-secondary flex-align" @click="fetchPending" :disabled="loading">
        <RefreshCw size="16" :class="{ 'loading-pulse': loading }" />
        Refresh
      </button>
    </div>

    <!-- Alert details after a decision is made -->
    <div v-if="decisionResult" class="card" style="border-color: var(--border-color); background-color: rgba(255,255,255,0.01); padding: 1.5rem;">
      <div class="flex-between" style="margin-bottom: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">
        <h3 style="margin-bottom: 0;" class="flex-align">
          <UserCheck size="16" style="color: var(--color-primary);" />
          Resumed Workload Result
        </h3>
        <button class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" @click="decisionResult = null">Close</button>
      </div>
      <div v-if="decisionResult.status === 'APPROVED'" style="display: flex; flex-direction: column; gap: 0.85rem;">
        <span class="badge badge-allowed" style="width: fit-content;">APPROVED & EXECUTED</span>
        <div>
          <label style="margin-bottom: 0.25rem;">LLM Output Completion</label>
          <div style="padding: 0.85rem; background-color: rgba(0,0,0,0.15); border-radius: 4px; border: 1px solid var(--border-color); font-size: 0.85rem; line-height: 1.6;">
            {{ decisionResult.llm_response }}
          </div>
        </div>
      </div>
      <div v-else>
        <span class="badge badge-blocked" style="width: fit-content; margin-bottom: 0.5rem;">REJECTED & BLOCKED</span>
        <p style="font-size: 0.85rem; margin-bottom: 0;">The workload execution request was aborted. Policy state remains locked.</p>
      </div>
    </div>

    <div class="card">
      <div v-if="loading && queue.length === 0" class="empty-state" style="padding: 5rem 0;">
        <RefreshCw class="loading-pulse" size="32" />
        <p style="margin-top: 1rem; font-size: 0.9rem;">Fetching pending approvals...</p>
      </div>

      <div v-else-if="queue.length === 0" class="empty-state" style="padding: 5rem 0;">
        <UserCheck size="48" style="color: var(--color-allowed); opacity: 0.8;" class="icon" />
        <p style="font-size: 0.9rem; margin-bottom: 0; color: var(--text-secondary);">Compliance clear. No pending human reviews in queue.</p>
      </div>

      <table v-else>
        <thead>
          <tr>
            <th>ID</th>
            <th>Agent</th>
            <th>Trigger Reason</th>
            <th>Prompt</th>
            <th>Requested Tool</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="req in queue" :key="req.request_id">
            <td style="font-family: var(--font-mono); font-size: 0.75rem;">{{ req.request_id }}</td>
            <td><strong>{{ req.agent_id.split('-')[0].toUpperCase() }}</strong></td>
            <td>
              <span class="badge badge-hitl" style="font-weight: 500;">
                {{ req.reason }}
              </span>
            </td>
            <td>
              <div 
                style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.8rem; color: var(--text-primary);"
                :title="req.prompt"
              >
                {{ req.prompt }}
              </div>
            </td>
            <td>
              <span v-if="req.requested_tool" class="badge badge-neutral" style="font-family: var(--font-mono); font-size: 0.7rem;">
                {{ req.requested_tool }}
              </span>
              <span v-else style="color: var(--text-muted); font-style: italic;">None</span>
            </td>
            <td>
              <div class="flex-align gap-sm">
                <button 
                  class="btn btn-danger" 
                  style="padding: 0.35rem 0.75rem; font-size: 0.75rem;" 
                  @click="decideRequest(req.agent_id, req.request_id, 'REJECTED')"
                  :disabled="actioningId === req.request_id"
                >
                  Reject
                </button>
                <button 
                  class="btn btn-success" 
                  style="padding: 0.35rem 0.75rem; font-size: 0.75rem;" 
                  @click="decideRequest(req.agent_id, req.request_id, 'APPROVED')"
                  :disabled="actioningId === req.request_id"
                >
                  <RefreshCw v-if="actioningId === req.request_id" class="loading-pulse" size="10" />
                  Approve
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { UserCheck, RefreshCw } from '@lucide/vue';

export default {
  name: 'ApprovalsView',
  components: {
    UserCheck,
    RefreshCw
  },
  props: {
    backendUrl: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      queue: [],
      loading: false,
      actioningId: null,
      decisionResult: null
    };
  },
  created() {
    this.fetchPending();
  },
  methods: {
    async fetchPending() {
      this.loading = true;
      try {
        const res = await fetch(`${this.backendUrl}/api/hitl/pending`);
        if (res.ok) {
          this.queue = await res.json();
          this.$emit('update-pending-count', this.queue.length);
        }
      } catch (err) {
        console.error('Failed to load pending queue:', err);
      } finally {
        this.loading = false;
      }
    },
    async decideRequest(agentId, requestId, decision) {
      this.actioningId = requestId;
      this.decisionResult = null;
      try {
        const res = await fetch(`${this.backendUrl}/api/agents/${agentId}/hitl/${requestId}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: decision })
        });
        
        const data = await res.json();
        
        if (res.ok) {
          this.decisionResult = {
            status: decision,
            llm_response: data.llm_response
          };
          this.$emit('audit-logs-updated');
          await this.fetchPending();
        }
      } catch (err) {
        console.error('Failed to resolve HITL approval:', err);
      } finally {
        this.actioningId = null;
      }
    }
  }
};
</script>
