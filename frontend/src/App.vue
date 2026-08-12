<template>
  <div class="app-container">
    <!-- Sidebar Navigation -->
    <aside class="sidebar">
      <div class="sidebar-brand">
        <Shield class="logo-icon" size="24" />
        <span>GOVERN SHIELD</span>
      </div>
      
      <ul class="sidebar-menu">
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'dashboard' }" 
            @click="switchTab('dashboard')"
          >
            <LayoutDashboard size="18" />
            Dashboard
          </button>
        </li>
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'agents' }" 
            @click="switchTab('agents')"
          >
            <Bot size="18" />
            Governed Agents
          </button>
        </li>
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'policies' }" 
            @click="switchTab('policies')"
          >
            <FileText size="18" />
            Policy Manager
          </button>
        </li>
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'versions' }" 
            @click="switchTab('versions')"
          >
            <History size="18" />
            Policy Commits
          </button>
        </li>
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'drift' }" 
            @click="switchTab('drift')"
            style="justify-content: space-between; display: flex; width: 100%;"
          >
            <span class="flex-align">
              <GitBranch size="18" />
              Drift Detector
            </span>
            <span v-if="anyAgentDrifted" class="badge badge-blocked" style="border-radius: 50%; width: 8px; height: 8px; padding: 0;"></span>
          </button>
        </li>
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'playground' }" 
            @click="switchTab('playground')"
          >
            <Play size="18" />
            AI Playground
          </button>
        </li>
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'hitl' }" 
            @click="switchTab('hitl')"
            style="justify-content: space-between; display: flex; width: 100%;"
          >
            <span class="flex-align">
              <UserCheck size="18" />
              HITL Reviews
            </span>
            <span v-if="pendingHitlCount > 0" class="badge badge-hitl" style="font-size: 0.65rem; padding: 0.1rem 0.4rem; font-weight: 700;">
              {{ pendingHitlCount }}
            </span>
          </button>
        </li>
        <li class="sidebar-item">
          <button 
            class="sidebar-link" 
            :class="{ active: currentTab === 'audit' }" 
            @click="switchTab('audit')"
          >
            <ScrollText size="18" />
            Audit Ledger
          </button>
        </li>
      </ul>

      <!-- Footer Info -->
      <footer class="sidebar-footer">
        <div>Connection: <span style="color: var(--color-allowed); font-weight: 600;">ACTIVE</span></div>
        <div>Mode: <span style="font-family: var(--font-mono); font-size: 0.65rem;">API GATEWAY</span></div>
        <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 0.5rem;">© 2026 Govern Shield v1.0</div>
      </footer>
    </aside>

    <!-- Main Workspace Content -->
    <main class="main-content">
      <!-- Dynamic Tab Mount -->
      <DashboardView 
        v-if="currentTab === 'dashboard'" 
        :backend-url="backendUrl" 
        @change-tab="switchTabWithParams"
        @update-pending-count="updateHitlCount"
      />
      
      <AgentsView 
        v-else-if="currentTab === 'agents'" 
        :backend-url="backendUrl" 
        @change-tab="switchTabWithParams"
      />
      
      <PoliciesView 
        v-else-if="currentTab === 'policies'" 
        :backend-url="backendUrl" 
        :initial-agent-id="selectedAgentId"
        @policy-updated="refreshGlobalStates"
      />
      
      <VersionsView 
        v-else-if="currentTab === 'versions'" 
        :backend-url="backendUrl" 
        :initial-agent-id="selectedAgentId"
      />
      
      <DriftView 
        v-else-if="currentTab === 'drift'" 
        :backend-url="backendUrl" 
        :initial-agent-id="selectedAgentId"
        @drift-state-changed="refreshGlobalStates"
      />
      
      <PlaygroundView 
        v-else-if="currentTab === 'playground'" 
        :backend-url="backendUrl" 
        :initial-agent-id="selectedAgentId"
        @hitl-queue-updated="pollPendingHitl"
      />
      
      <ApprovalsView 
        v-else-if="currentTab === 'hitl'" 
        :backend-url="backendUrl" 
        @update-pending-count="updateHitlCount"
      />
      
      <AuditView 
        v-else-if="currentTab === 'audit'" 
        :backend-url="backendUrl" 
      />
    </main>
  </div>
</template>

<script>
import { 
  Shield, 
  LayoutDashboard, 
  Bot, 
  FileText, 
  History, 
  GitBranch, 
  Play, 
  UserCheck, 
  ScrollText 
} from '@lucide/vue';

// Import Views
import DashboardView from './components/DashboardView.vue';
import AgentsView from './components/AgentsView.vue';
import PoliciesView from './components/PoliciesView.vue';
import VersionsView from './components/VersionsView.vue';
import DriftView from './components/DriftView.vue';
import PlaygroundView from './components/PlaygroundView.vue';
import ApprovalsView from './components/ApprovalsView.vue';
import AuditView from './components/AuditView.vue';

export default {
  name: 'App',
  components: {
    Shield,
    LayoutDashboard,
    Bot,
    FileText,
    History,
    GitBranch,
    Play,
    UserCheck,
    ScrollText,
    DashboardView,
    AgentsView,
    PoliciesView,
    VersionsView,
    DriftView,
    PlaygroundView,
    ApprovalsView,
    AuditView
  },
  data() {
    return {
      currentTab: 'dashboard',
      selectedAgentId: 'customer-support-agent',
      backendUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
      pendingHitlCount: 0,
      anyAgentDrifted: false,
      pollInterval: null
    };
  },
  created() {
    this.refreshGlobalStates();
    // Start background polling for HITL queue and Drift states
    this.pollInterval = setInterval(this.refreshGlobalStates, 10000);
  },
  beforeUnmount() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
    }
  },
  methods: {
    switchTab(tab) {
      this.currentTab = tab;
    },
    switchTabWithParams(tab, agentId = null) {
      if (agentId) {
        this.selectedAgentId = agentId;
      }
      this.currentTab = tab;
    },
    updateHitlCount(count) {
      this.pendingHitlCount = count;
    },
    async pollPendingHitl() {
      try {
        const res = await fetch(`${this.backendUrl}/api/hitl/pending`);
        if (res.ok) {
          const data = await res.json();
          this.pendingHitlCount = data.length;
        }
      } catch (err) {
        console.error('Error polling pending HITL approvals:', err);
      }
    },
    async pollDriftStatus() {
      try {
        const res = await fetch(`${this.backendUrl}/api/agents`);
        if (res.ok) {
          const agents = await res.json();
          this.anyAgentDrifted = agents.some(a => a.is_drifted);
        }
      } catch (err) {
        console.error('Error polling drift status:', err);
      }
    },
    refreshGlobalStates() {
      this.pollPendingHitl();
      this.pollDriftStatus();
    }
  }
};
</script>
