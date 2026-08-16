<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>Policy Drift Detector</h1>
        <p class="subtitle" style="margin-bottom: 0;">Monitors alignment between Git-approved source code policies and active runtime enforcement engines.</p>
      </div>
      <div class="flex-align gap-sm">
        <label style="margin-bottom: 0; color: var(--text-secondary); text-transform: none; font-weight: 500;">Select Agent:</label>
        <select v-model="selectedAgent" style="width: 220px;" @change="checkDrift">
          <option value="customer-support-agent">Customer Support Agent</option>
          <option value="loan-processor-agent">Loan Processor Agent</option>
        </select>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="card empty-state" style="padding: 5rem 0;">
      <RefreshCw class="loading-pulse" size="32" />
      <p style="margin-top: 1rem; font-size: 0.9rem;">Comparing policies...</p>
    </div>

    <div v-else>
      <!-- Big Status Banner -->
      <div class="card" :style="{ borderColor: driftReport.is_drifted ? 'var(--color-blocked)' : 'var(--color-allowed)', backgroundColor: driftReport.is_drifted ? 'var(--color-blocked-light)' : 'var(--color-allowed-light)', padding: '2rem' }">
        <div class="flex-between" style="align-items: center;">
          <div class="flex-align gap-md">
            <ShieldAlert v-if="driftReport.is_drifted" size="48" style="color: var(--color-blocked);" />
            <ShieldCheck v-else size="48" style="color: var(--color-allowed);" />
            <div>
              <h2 style="margin-bottom: 0.25rem; font-size: 1.5rem;">
                {{ driftReport.is_drifted ? 'POLICY DRIFT DETECTED' : 'POLICY STATE SECURED' }}
              </h2>
              <p style="margin-bottom: 0; color: var(--text-primary);">
                {{ driftReport.is_drifted ? 'Active runtime engine is running modified policy settings bypassing Git CI/CD control.' : 'Authoritative Git configuration aligns perfectly with runtime enforcement.' }}
              </p>
            </div>
          </div>
          
          <button 
            v-if="driftReport.is_drifted" 
            class="btn btn-success flex-align" 
            @click="revertDrift" 
            :disabled="reverting"
          >
            <RefreshCw v-if="reverting" class="loading-pulse" size="14" />
            <RefreshCw v-else size="14" />
            Revert to Git Policy
          </button>
        </div>
      </div>

      <!-- Main Layout Grid -->
      <div class="grid-2">
        <!-- Left Panel: Drift Diff Breakdown -->
        <div class="card" style="min-height: 380px;">
          <h2>Policy Field Diffs</h2>
          
          <div v-if="!driftReport.is_drifted" class="empty-state" style="padding: 5rem 0;">
            <ShieldCheck size="40" style="color: var(--color-allowed); opacity: 0.8;" class="icon" />
            <p style="font-size: 0.85rem; margin-bottom: 0; color: var(--text-secondary);">No policy drifts found. All settings align.</p>
          </div>

          <table v-else>
            <thead>
              <tr>
                <th>Property Path</th>
                <th>Git Value</th>
                <th>Runtime Value</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="diff in driftReport.differences" :key="diff.field">
                <td style="font-family: var(--font-mono); font-size: 0.8rem; color: var(--text-primary); font-weight: 500;">
                  {{ diff.field }}
                </td>
                <td style="font-size: 0.8rem; font-family: var(--font-mono); color: var(--color-allowed);">
                  {{ formatDiffValue(diff.git_value) }}
                </td>
                <td style="font-size: 0.8rem; font-family: var(--font-mono); color: var(--color-blocked);">
                  {{ formatDiffValue(diff.runtime_value) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Right Panel: Simulation Actions -->
        <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <h2>Drift Simulator</h2>
            <p style="font-size: 0.85rem; line-height: 1.6; color: var(--text-secondary); margin-bottom: 1.5rem;">
              Simulate out-of-band manual policy changes. This action modifies the backend runtime database directly (bypassing Git/CI) to demonstrate how the drift engine alerts operators of non-compliant configurations.
            </p>

            <div class="form-group">
              <label>Select Drift Template</label>
              <select v-model="driftTemplate" style="width: 100%;">
                <option value="threshold">Alter HITL Threshold (Set to 0.9)</option>
                <option value="tool">Disallow Support Tool (Remove 'customer_lookup')</option>
              </select>
            </div>
          </div>

          <button 
            class="btn btn-danger flex-align" 
            style="width: 100%; margin-top: 1rem;" 
            @click="simulateDrift" 
            :disabled="simulating"
          >
            <ShieldAlert size="14" />
            Inject Out-of-Band Modification
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ShieldCheck, ShieldAlert, RefreshCw } from '@lucide/vue';
import * as yaml from 'js-yaml';

export default {
  name: 'DriftView',
  components: {
    ShieldCheck,
    ShieldAlert,
    RefreshCw
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
      loading: false,
      simulating: false,
      reverting: false,
      driftTemplate: 'threshold',
      driftReport: {
        is_drifted: false,
        differences: []
      }
    };
  },
  created() {
    this.checkDrift();
  },
  methods: {
    async checkDrift() {
      this.loading = true;
      try {
        const res = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/drift`);
        if (res.ok) {
          this.driftReport = await res.json();
        }
      } catch (err) {
        console.error('Failed to run drift comparison:', err);
      } finally {
        this.loading = false;
      }
    },
    async simulateDrift() {
      this.simulating = true;
      try {
        // First retrieve active Git policy to modify
        const gitRes = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/policy?version=latest_git`);
        if (!gitRes.ok) return;
        const gitData = await gitRes.json();
        
        const doc = yaml.load(gitData.policy_yaml);
        
        // Inject modifications based on template
        if (this.driftTemplate === 'threshold') {
          doc.hitl = doc.hitl || {};
          doc.hitl.threshold = 0.9;
        } else if (this.driftTemplate === 'model') {
          doc.approved_models = doc.approved_models || [];
          if (!doc.approved_models.includes('openai/gpt-4o')) {
            doc.approved_models.push('openai/gpt-4o');
          }
        } else if (this.driftTemplate === 'tool') {
          doc.allowed_tools = (doc.allowed_tools || []).filter(t => t.name !== 'customer_lookup');
        }
        
        const modifiedYaml = yaml.dump(doc);
        
        const simRes = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/policy/drift-simulate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ policy_yaml: modifiedYaml })
        });
        
        if (simRes.ok) {
          this.$emit('drift-state-changed');
          await this.checkDrift();
        }
      } catch (err) {
        console.error('Failed to simulate drift:', err);
      } finally {
        this.simulating = false;
      }
    },
    async revertDrift() {
      this.reverting = true;
      try {
        const res = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/policy/drift-revert`, {
          method: 'POST'
        });
        if (res.ok) {
          this.$emit('drift-state-changed');
          await this.checkDrift();
        }
      } catch (err) {
        console.error('Failed to revert drift:', err);
      } finally {
        this.reverting = false;
      }
    },
    formatDiffValue(val) {
      if (val === null || val === undefined) return 'None';
      if (typeof val === 'object') return JSON.stringify(val);
      return val.toString();
    }
  }
};
</script>
