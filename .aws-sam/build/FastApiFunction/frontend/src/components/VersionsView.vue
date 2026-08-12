<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>Policy Deployment History</h1>
        <p class="subtitle" style="margin-bottom: 0;">Immutable ledger of all Git-approved policies deployed for this agent node. Retrieve historic records by Git commit SHA.</p>
      </div>
      <div class="flex-align gap-sm">
        <label style="margin-bottom: 0; color: var(--text-secondary); text-transform: none; font-weight: 500;">Select Agent:</label>
        <select v-model="selectedAgent" style="width: 220px;" @change="fetchVersions">
          <option value="customer-support-agent">Customer Support Agent</option>
          <option value="loan-processor-agent">Loan Processor Agent</option>
        </select>
      </div>
    </div>

    <!-- Active SHA Context Banner -->
    <div class="alert alert-info flex-between" style="align-items: center; margin-bottom: 1.5rem;">
      <div class="flex-align">
        <GitBranch size="16" />
        <span>Currently Active Runtime Commit: <strong style="font-family: var(--font-mono); font-size: 0.85rem;">{{ activeSha }}</strong></span>
      </div>
      <span class="badge badge-allowed">Active in Production</span>
    </div>

    <div class="grid-2" style="align-items: flex-start;">
      <!-- Left Card: Table of historical commits -->
      <div class="card">
        <div class="flex-between" style="border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem; margin-bottom: 1rem;">
          <h2 style="margin-bottom: 0;">Policy Commits</h2>
          <button class="btn btn-secondary" style="padding: 0.3rem 0.75rem; font-size: 0.75rem;" @click="fetchVersions" :disabled="loading">
            <RefreshCw size="12" :class="{ 'loading-pulse': loading }" />
          </button>
        </div>

        <div v-if="loading && versions.length === 0" class="empty-state" style="padding: 3rem 0;">
          <RefreshCw class="loading-pulse" size="24" />
        </div>

        <div v-else-if="versions.length === 0" class="empty-state" style="padding: 3rem 0;">
          <History size="32" class="icon" />
          <p style="font-size: 0.85rem; margin-bottom: 0;">No policy commits found for this agent.</p>
        </div>

        <table v-else>
          <thead>
            <tr>
              <th>Commit</th>
              <th>Version</th>
              <th>Deployed At</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="v in versions" 
              :key="v.commit_sha" 
              :style="{ backgroundColor: selectedVersion && selectedVersion.commit_sha === v.commit_sha ? 'rgba(255,255,255,0.03)' : 'transparent' }"
            >
              <td>
                <div class="flex-align gap-sm">
                  <span style="font-family: var(--font-mono); font-size: 0.8rem; font-weight: 500;">
                    {{ v.commit_sha.slice(0, 10) }}
                  </span>
                  <span v-if="v.commit_sha === activeSha" class="badge badge-allowed" style="font-size: 0.6rem; padding: 0.1rem 0.35rem;">
                    Active
                  </span>
                </div>
              </td>
              <td>v{{ v.version }}</td>
              <td style="font-size: 0.8rem;">{{ formatDateTime(v.timestamp) }}</td>
              <td>
                <button class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" @click="inspectVersion(v.commit_sha)">
                  Inspect Code
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Right Card: Inspect YAML view -->
      <div class="card" style="min-height: 420px; display: flex; flex-direction: column; justify-content: space-between;">
        <div style="width: 100%;">
          <div class="flex-between" style="border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem; margin-bottom: 1rem;">
            <h2 style="margin-bottom: 0;">Commit Inspection</h2>
            <span v-if="selectedVersion" class="badge badge-neutral" style="font-family: var(--font-mono); font-size: 0.7rem;">
              SHA: {{ selectedVersion.commit_sha.slice(0,10) }}
            </span>
          </div>

          <div v-if="inspecting" class="empty-state" style="padding: 6rem 0;">
            <RefreshCw class="loading-pulse" size="24" />
          </div>

          <div v-else-if="!selectedVersion" class="empty-state" style="padding: 6rem 0; color: var(--text-muted);">
            <ScrollText size="32" class="icon" />
            <p style="font-size: 0.85rem; margin-bottom: 0;">Select a commit version from the table to inspect its YAML policy representation.</p>
          </div>

          <div v-else>
            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.25rem; padding: 0.75rem; background-color: rgba(255,255,255,0.01); border-radius: 4px; border: 1px solid var(--border-color);">
              <div><span>Deployed By:</span> <strong style="color: var(--text-primary);">{{ selectedVersion.updated_by }}</strong></div>
              <div><span>Timestamp:</span> <strong style="color: var(--text-primary);">{{ formatDateTime(selectedVersion.timestamp) }}</strong></div>
            </div>
            
            <textarea 
              class="code-editor" 
              v-model="selectedVersion.policy_yaml" 
              disabled 
              style="min-height: 250px; background-color: #030406; border-color: rgba(255,255,255,0.05);"
            ></textarea>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { GitBranch, RefreshCw, History, ScrollText } from '@lucide/vue';

export default {
  name: 'VersionsView',
  components: {
    GitBranch,
    RefreshCw,
    History,
    ScrollText
  },
  props: {
    backendUrl: {
      type: String,
      required: true
    },
    initialAgentId: {
      type: String,
      default: 'customer-support-agent'
    }
  },
  data() {
    return {
      selectedAgent: this.initialAgentId,
      versions: [],
      activeSha: 'unknown',
      selectedVersion: null,
      loading: false,
      inspecting: false
    };
  },
  created() {
    this.fetchVersions();
  },
  methods: {
    async fetchVersions() {
      this.loading = true;
      this.selectedVersion = null;
      try {
        // Get active commit SHA pointer
        const activeRes = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/policy?version=runtime`);
        if (activeRes.ok) {
          const activeData = await activeRes.json();
          this.activeSha = activeData.commit_sha || 'unknown';
        }

        // Get historical list of commits
        const res = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/versions`);
        if (res.ok) {
          this.versions = await res.json();
          
          // Proactively inspect the first version (active/latest) if available
          if (this.versions.length > 0) {
            this.inspectVersion(this.versions[0].commit_sha);
          }
        }
      } catch (err) {
        console.error('Failed to load version history:', err);
      } finally {
        this.loading = false;
      }
    },
    async inspectVersion(commitSha) {
      this.inspecting = true;
      try {
        const res = await fetch(`${this.backendUrl}/api/policies/${this.selectedAgent}/${commitSha}`);
        if (res.ok) {
          this.selectedVersion = await res.json();
        }
      } catch (err) {
        console.error('Failed to retrieve historic policy code:', err);
      } finally {
        this.inspecting = false;
      }
    },
    formatDateTime(isoString) {
      if (!isoString) return '';
      const date = new Date(isoString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  }
};
</script>
