<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>Governance Ledger</h1>
        <p class="subtitle" style="margin-bottom: 0;">Authorized event ledger tracking policy validation cycles, runtime interceptions, and administrative compliance decisions.</p>
      </div>
      <button class="btn btn-secondary flex-align" @click="fetchLogs" :disabled="loading">
        <RefreshCw size="16" :class="{ 'loading-pulse': loading }" />
        Refresh
      </button>
    </div>

    <!-- Filters Panel -->
    <div class="card" style="padding: 1.25rem; display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; margin-bottom: 1.5rem; border-color: rgba(255,255,255,0.06); background-color: rgba(255,255,255,0.01);">
      <div class="form-group" style="margin-bottom: 0;">
        <label>Filter Agent</label>
        <select v-model="filterAgent">
          <option :value="null">All Agents</option>
          <option value="customer-support-agent">Customer Support Agent</option>
          <option value="loan-processor-agent">Loan Processor Agent</option>
        </select>
      </div>

      <div class="form-group" style="margin-bottom: 0;">
        <label>Event Type</label>
        <select v-model="filterType">
          <option :value="null">All Events</option>
          <option value="POLICY_DEPLOYMENT">Policy Deployment</option>
          <option value="POLICY_VALIDATION">Policy Validation Failures</option>
          <option value="DRIFT_DETECTED">Policy Drift Warnings</option>
          <option value="WORKLOAD_ALLOWED">Workload Authorized</option>
          <option value="WORKLOAD_BLOCKED">Workload Blocked</option>
          <option value="HITL_TRIGGERED">HITL Suspended</option>
          <option value="HITL_DECISION">HITL Approvals/Rejections</option>
        </select>
      </div>

      <div class="form-group" style="margin-bottom: 0;">
        <label>Severity Level</label>
        <select v-model="filterSeverity">
          <option :value="null">All Severities</option>
          <option value="INFO">INFO (Normal Operations)</option>
          <option value="WARNING">WARNING (Review Required)</option>
          <option value="ERROR">ERROR (Compliance Block)</option>
        </select>
      </div>
    </div>

    <!-- Logs Table -->
    <div class="card">
      <div v-if="loading && logs.length === 0" class="empty-state" style="padding: 5rem 0;">
        <RefreshCw class="loading-pulse" size="32" />
        <p style="margin-top: 1rem; font-size: 0.9rem;">Fetching audit log ledger...</p>
      </div>

      <div v-else-if="filteredLogs.length === 0" class="empty-state" style="padding: 5rem 0;">
        <History size="48" style="color: var(--text-muted); opacity: 0.6;" class="icon" />
        <p style="font-size: 0.9rem; margin-bottom: 0;">No audit events match current filter conditions.</p>
      </div>

      <div v-else>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Agent</th>
              <th>Severity</th>
              <th>Event Type</th>
              <th>Message Summary</th>
              <th>Audit Trail</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="log in filteredLogs" :key="log.log_id">
              <!-- Log row -->
              <tr>
                <td style="font-size: 0.8rem; font-family: var(--font-mono); white-space: nowrap;">
                  {{ formatDateTime(log.timestamp) }}
                </td>
                <td>
                  <span style="font-size: 0.75rem; font-weight: 600; font-family: var(--font-mono);">
                    {{ log.agent_id.split('-')[0].toUpperCase() }}
                  </span>
                </td>
                <td>
                  <span :class="getSeverityClass(log.severity)" class="badge" style="font-size: 0.65rem; padding: 0.15rem 0.45rem;">
                    {{ log.severity }}
                  </span>
                </td>
                <td>
                  <span :class="getEventBadgeClass(log.event_type)" class="badge" style="font-size: 0.65rem; padding: 0.15rem 0.45rem; font-weight: 600;">
                    {{ log.event_type }}
                  </span>
                </td>
                <td style="font-size: 0.85rem; color: var(--text-primary);">
                  {{ log.message }}
                  <span v-if="log.commit_sha && log.commit_sha !== 'OUT-OF-BAND-MANUAL-CHANGE'" style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); display: block; margin-top: 0.15rem;">
                    Commit: {{ log.commit_sha.slice(0, 10) }}
                  </span>
                </td>
                <td>
                  <button 
                    class="btn btn-secondary" 
                    style="padding: 0.25rem 0.5rem; font-size: 0.75rem;" 
                    @click="toggleDetails(log.log_id)"
                  >
                    {{ expandedIds.includes(log.log_id) ? 'Collapse' : 'Inspect JSON' }}
                  </button>
                </td>
              </tr>
              <!-- Expandable details block -->
              <tr v-if="expandedIds.includes(log.log_id)" style="background-color: rgba(0,0,0,0.2);">
                <td colspan="6" style="padding: 1.25rem; border-bottom: 1px solid var(--border-color);">
                  <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                    <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-primary); text-transform: uppercase;">Raw Audit Metadata Ledger (JSON)</span>
                    <pre style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-secondary); background-color: #030406; padding: 1rem; border-radius: var(--border-radius-md); border: 1px solid rgba(255,255,255,0.05); max-height: 250px; overflow-y: auto; line-height: 1.45;">{{ JSON.stringify(log, null, 2) }}</pre>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { History, RefreshCw } from '@lucide/vue';

export default {
  name: 'AuditView',
  components: {
    History,
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
      logs: [],
      filterAgent: null,
      filterType: null,
      filterSeverity: null,
      expandedIds: [],
      loading: false
    };
  },
  computed: {
    filteredLogs() {
      return this.logs.filter(log => {
        if (this.filterAgent && log.agent_id !== this.filterAgent) return false;
        if (this.filterType && log.event_type !== this.filterType) return false;
        if (this.filterSeverity && log.severity !== this.filterSeverity) return false;
        return true;
      });
    }
  },
  created() {
    this.fetchLogs();
  },
  methods: {
    async fetchLogs() {
      this.loading = true;
      try {
        const res = await fetch(`${this.backendUrl}/api/audit-logs`);
        if (res.ok) {
          this.logs = await res.json();
        }
      } catch (err) {
        console.error('Failed to load audit ledger:', err);
      } finally {
        this.loading = false;
      }
    },
    toggleDetails(id) {
      if (this.expandedIds.includes(id)) {
        this.expandedIds = this.expandedIds.filter(i => i !== id);
      } else {
        this.expandedIds.push(id);
      }
    },
    formatDateTime(isoString) {
      if (!isoString) return '';
      const date = new Date(isoString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    },
    getSeverityClass(sev) {
      if (sev === 'ERROR') return 'badge-blocked';
      if (sev === 'WARNING') return 'badge-hitl';
      return 'badge-neutral';
    },
    getEventBadgeClass(type) {
      if (type.includes('BLOCKED') || type.includes('ERROR')) return 'badge-blocked';
      if (type.includes('TRIGGERED') || type.includes('WARNING')) return 'badge-hitl';
      if (type.includes('DEPLOYMENT') || type.includes('ALLOWED')) return 'badge-allowed';
      return 'badge-neutral';
    }
  }
};
</script>
