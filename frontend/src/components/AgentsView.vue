<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>Governed AI Agents</h1>
        <p class="subtitle" style="margin-bottom: 0;">Active agent nodes with details of their model authorizations, tools, and code-alignment status.</p>
      </div>
      <button class="btn btn-secondary flex-align" @click="fetchAgents" :disabled="loading">
        <RefreshCw :class="{ 'loading-pulse': loading }" size="16" />
        Refresh
      </button>
    </div>

    <div v-if="loading && agents.length === 0" class="empty-state">
      <Bot class="loading-pulse" size="48" style="color: var(--color-primary);" />
      <p style="margin-top: 1rem;">Loading agent registry...</p>
    </div>

    <div v-else class="grid-2">
      <!-- Agent Card -->
      <div v-for="agent in agents" :key="agent.agent_id" class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div class="flex-between" style="margin-bottom: 1rem; align-items: flex-start;">
            <div>
              <h2 style="margin-bottom: 0.25rem;">{{ agent.name }}</h2>
              <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted);">
                {{ agent.agent_id }}
              </span>
            </div>
            
            <span 
              class="badge" 
              :class="agent.is_drifted ? 'badge-blocked' : 'badge-allowed'"
            >
              <ShieldAlert v-if="agent.is_drifted" size="12" />
              <ShieldCheck v-else size="12" />
              {{ agent.is_drifted ? 'DRIFTED' : 'COMPLIANT' }}
            </span>
          </div>

          <p style="font-size: 0.85rem; line-height: 1.6; margin-bottom: 1.5rem;">
            {{ getAgentDescription(agent.agent_id) }}
          </p>

          <!-- Specifications List -->
          <div style="display: flex; flex-direction: column; gap: 0.85rem; padding: 1rem; background-color: rgba(255,255,255,0.02); border-radius: var(--border-radius-md); border: 1px solid var(--border-color); margin-bottom: 1.5rem;">
            <!-- Git Version Info -->
            <div class="flex-between" style="font-size: 0.8rem;">
              <span style="color: var(--text-muted); font-weight: 500;">Git Commit SHA</span>
              <span style="font-family: var(--font-mono); color: var(--text-primary); font-size: 0.75rem; background-color: rgba(255,255,255,0.05); padding: 0.1rem 0.35rem; border-radius: 4px;">
                {{ agent.git_commit.slice(0, 10) }}
              </span>
            </div>

            <!-- Active Policy Version -->
            <div class="flex-between" style="font-size: 0.8rem;">
              <span style="color: var(--text-muted); font-weight: 500;">Active Policy Version</span>
              <span style="font-weight: 600; color: var(--text-primary);">v{{ agent.active_version }}</span>
            </div>

            <!-- Models Authorization -->
            <div style="font-size: 0.8rem;">
              <span style="color: var(--text-muted); font-weight: 500; display: block; margin-bottom: 0.35rem;">Approved Models</span>
              <div style="display: flex; flex-wrap: wrap; gap: 0.35rem;">
                <span v-for="model in agent.approved_models" :key="model" class="badge badge-neutral" style="font-family: var(--font-mono); font-size: 0.7rem; font-weight: 500;">
                  {{ model }}
                </span>
              </div>
            </div>

            <!-- Tools Authorization -->
            <div style="font-size: 0.8rem;">
              <span style="color: var(--text-muted); font-weight: 500; display: block; margin-bottom: 0.35rem;">Authorized Tools</span>
              <div style="display: flex; flex-wrap: wrap; gap: 0.35rem;">
                <span v-for="tool in agent.allowed_tools" :key="tool" class="badge badge-neutral" style="font-family: var(--font-mono); font-size: 0.7rem; font-weight: 500;">
                  {{ tool }}
                </span>
                <span v-if="agent.allowed_tools.length === 0" style="color: var(--text-muted); font-style: italic;">
                  No tools authorized
                </span>
              </div>
            </div>

            <!-- Last Synchronized -->
            <div class="flex-between" style="font-size: 0.8rem;">
              <span style="color: var(--text-muted); font-weight: 500;">Last Deployed</span>
              <span style="color: var(--text-secondary);">{{ formatDateTime(agent.last_deployed) }}</span>
            </div>
          </div>
        </div>

        <!-- Card Action Panel -->
        <div class="flex-align gap-sm" style="margin-top: 1rem; width: 100%;">
          <button class="btn btn-secondary" style="flex: 1;" @click="$emit('change-tab', 'policies', agent.agent_id)">
            View Policy File
          </button>
          <button class="btn btn-primary" style="flex: 1;" @click="$emit('change-tab', 'playground', agent.agent_id)">
            Test AI Workload
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Bot, RefreshCw, ShieldCheck, ShieldAlert } from '@lucide/vue';

export default {
  name: 'AgentsView',
  components: {
    Bot,
    RefreshCw,
    ShieldCheck,
    ShieldAlert
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
      loading: false
    };
  },
  created() {
    this.fetchAgents();
  },
  methods: {
    async fetchAgents() {
      this.loading = true;
      try {
        const res = await fetch(`${this.backendUrl}/api/agents`);
        if (res.ok) {
          this.agents = await res.json();
        }
      } catch (err) {
        console.error('Failed to load agents:', err);
      } finally {
        this.loading = false;
      }
    },
    getAgentDescription(id) {
      if (id === 'customer-support-agent') {
        return 'Automated client assistance agent. Resolves inquiries, performs order status searches via read tools, and dispatches support notifications via write tools.';
      }
      if (id === 'loan-processor-agent') {
        return 'Financial loan advisor agent. Conducts credit rating checks via read tools and executes loan approval terms via high-risk write tools.';
      }
      return 'AI agent workload running governed scripts.';
    },
    formatDateTime(isoString) {
      if (!isoString) return '';
      const date = new Date(isoString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  }
};
</script>
