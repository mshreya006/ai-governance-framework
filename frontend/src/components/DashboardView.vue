<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>Governance Control Center</h1>
        <p class="subtitle" style="margin-bottom: 0;">Real-time policy compliance, drift monitoring, and human review ledger.</p>
      </div>
      <button class="btn btn-secondary flex-align" @click="fetchDashboardData" :disabled="loading">
        <RefreshCw :class="{ 'loading-pulse': loading }" size="16" />
        Refresh
      </button>
    </div>

    <!-- Status Cards Grid -->
    <div class="grid-4" style="margin-bottom: 2rem;">
      <!-- Governed Agents KPI -->
      <div class="card flex-column" style="margin-bottom: 0;">
        <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Governed Agents</span>
        <div class="flex-between" style="margin-top: 0.5rem; align-items: flex-end;">
          <span style="font-size: 2.25rem; font-weight: 700; line-height: 1;">{{ agents.length }}</span>
          <Bot size="32" style="color: var(--color-primary); opacity: 0.8;" />
        </div>
      </div>

      <!-- Drift KPI -->
      <div class="card flex-column" style="margin-bottom: 0;">
        <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Drift Status</span>
        <div class="flex-between" style="margin-top: 0.5rem; align-items: flex-end;">
          <span 
            style="font-size: 1.15rem; font-weight: 700;"
            :class="driftedCount > 0 ? 'badge badge-blocked' : 'badge badge-allowed'"
          >
            {{ driftedCount > 0 ? `${driftedCount} Drifted` : 'In Sync' }}
          </span>
          <GitBranch size="32" :style="{ color: driftedCount > 0 ? 'var(--color-blocked)' : 'var(--color-allowed)', opacity: 0.8 }" />
        </div>
      </div>

      <!-- HITL Approvals KPI -->
      <div class="card flex-column" style="margin-bottom: 0;">
        <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">Pending Approvals</span>
        <div class="flex-between" style="margin-top: 0.5rem; align-items: flex-end;">
          <span 
            style="font-size: 1.15rem; font-weight: 700;"
            :class="pendingHitlCount > 0 ? 'badge badge-hitl' : 'badge badge-neutral'"
          >
            {{ pendingHitlCount }} Pending
          </span>
          <UserCheck size="32" :style="{ color: pendingHitlCount > 0 ? 'var(--color-hitl)' : 'var(--text-muted)', opacity: 0.8 }" />
        </div>
      </div>

      <!-- API Health KPI -->
      <div class="card flex-column" style="margin-bottom: 0;">
        <span style="font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase;">System Health</span>
        <div class="flex-between" style="margin-top: 0.5rem; align-items: flex-end;">
          <span class="badge badge-allowed" style="font-size: 0.85rem; padding: 0.35rem 0.75rem;">
            Healthy
          </span>
          <Activity size="32" style="color: var(--color-allowed); opacity: 0.8;" />
        </div>
      </div>
    </div>

    <!-- Main Dashboard Section -->
    <div class="grid-2">
      <!-- Pending Reviews Card -->
      <div class="card">
        <div class="flex-between" style="margin-bottom: 1rem;">
          <h2 style="margin-bottom: 0;">Pending Review Queue</h2>
          <button class="btn btn-secondary" style="padding: 0.3rem 0.75rem; font-size: 0.75rem;" @click="$emit('change-tab', 'hitl')">
            Manage Queue
          </button>
        </div>
        
        <div v-if="pendingApprovals.length === 0" class="empty-state" style="padding: 2rem 0;">
          <UserCheck class="icon" size="32" />
          <p style="font-size: 0.85rem; margin-bottom: 0;">All Human-in-the-loop requests are cleared.</p>
        </div>
        
        <table v-else>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Reason</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="req in pendingApprovals.slice(0, 3)" :key="req.request_id">
              <td><strong>{{ req.agent_id.split('-')[0].toUpperCase() }}</strong></td>
              <td>
                <span class="badge badge-hitl" style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  {{ req.reason }}
                </span>
              </td>
              <td>{{ formatTime(req.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Recent Audit Events Card -->
      <div class="card">
        <div class="flex-between" style="margin-bottom: 1rem;">
          <h2 style="margin-bottom: 0;">Recent Audit Events</h2>
          <button class="btn btn-secondary" style="padding: 0.3rem 0.75rem; font-size: 0.75rem;" @click="$emit('change-tab', 'audit')">
            View Ledger
          </button>
        </div>
        
        <div v-if="auditLogs.length === 0" class="empty-state" style="padding: 2rem 0;">
          <History class="icon" size="32" />
          <p style="font-size: 0.85rem; margin-bottom: 0;">No governance events logged.</p>
        </div>
        
        <table v-else>
          <thead>
            <tr>
              <th>Type</th>
              <th>Message</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in auditLogs.slice(0, 5)" :key="log.log_id">
              <td>
                <span :class="getEventBadgeClass(log.event_type)" class="badge">
                  {{ log.event_type }}
                </span>
              </td>
              <td>{{ log.message }}</td>
              <td>{{ formatTime(log.timestamp) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { Bot, GitBranch, UserCheck, Activity, RefreshCw, History } from '@lucide/vue';

export default {
  name: 'DashboardView',
  components: {
    Bot,
    GitBranch,
    UserCheck,
    Activity,
    RefreshCw,
    History
  },
  props: {
    backendUrl: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      agents: [],
      pendingApprovals: [],
      auditLogs: [],
      loading: false
    };
  },
  computed: {
    driftedCount() {
      return this.agents.filter(a => a.is_drifted).length;
    },
    pendingHitlCount() {
      return this.pendingApprovals.length;
    }
  },
  created() {
    this.fetchDashboardData();
  },
  methods: {
    async fetchDashboardData() {
      this.loading = true;
      try {
        // Fetch Agents list
        const agentsRes = await fetch(`${this.backendUrl}/api/agents`);
        if (agentsRes.ok) this.agents = await agentsRes.json();

        // Fetch Pending HITL Requests
        const hitlRes = await fetch(`${this.backendUrl}/api/hitl/pending`);
        if (hitlRes.ok) {
          this.pendingApprovals = await hitlRes.json();
          this.$emit('update-pending-count', this.pendingApprovals.length);
        }

        // Fetch Audit Logs
        const auditRes = await fetch(`${this.backendUrl}/api/audit-logs`);
        if (auditRes.ok) this.auditLogs = await auditRes.json();
        
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        this.loading = false;
      }
    },
    formatTime(isoString) {
      if (!isoString) return '';
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
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
