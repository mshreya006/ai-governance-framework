<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>Policy Manager</h1>
        <p class="subtitle" style="margin-bottom: 0;">View, edit, and synchronize Git policy configurations. Deploy changes via the CI/CD pipeline simulator.</p>
      </div>
      <div class="flex-align gap-sm">
        <label style="margin-bottom: 0; color: var(--text-secondary); text-transform: none; font-weight: 500;">Select Agent:</label>
        <select v-model="selectedAgent" style="width: 220px;" @change="loadActivePolicy">
          <option value="customer-support-agent">Customer Support Agent</option>
          <option value="loan-processor-agent">Loan Processor Agent</option>
        </select>
      </div>
    </div>

    <!-- Alert / Validation Message Section -->
    <div v-if="deployStatus.message" :class="deployStatus.success ? 'alert alert-success' : 'alert alert-danger'">
      <ShieldCheck v-if="deployStatus.success" size="18" style="margin-top: 0.1rem; flex-shrink: 0;" />
      <AlertOctagon v-else size="18" style="margin-top: 0.1rem; flex-shrink: 0;" />
      <div style="display: flex; flex-direction: column;">
        <strong style="margin-bottom: 0.25rem;">{{ deployStatus.success ? 'CI/CD Deploy Success' : 'CI/CD Build Failed & Blocked' }}</strong>
        <span>{{ deployStatus.message }}</span>
        <ul v-if="deployStatus.errors && deployStatus.errors.length > 0" style="margin-top: 0.5rem; margin-left: 1rem; font-size: 0.8rem; font-family: var(--font-mono);">
          <li v-for="err in deployStatus.errors" :key="err">{{ err }}</li>
        </ul>
      </div>
    </div>

    <!-- Main Workspace Grid -->
    <div class="grid-2">
      <!-- Left Side: Form Editor or raw view options -->
      <div class="card" style="display: flex; flex-direction: column;">
        <div class="flex-between" style="border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem; margin-bottom: 1.5rem;">
          <h2 style="margin-bottom: 0;">Structured Form Editor</h2>
          <span class="badge badge-neutral">Sync Enabled</span>
        </div>

        <div v-if="loadingPolicy" class="empty-state" style="padding: 5rem 0;">
          <RefreshCw class="loading-pulse" size="32" />
          <p style="margin-top: 1rem; font-size: 0.9rem;">Fetching active policy...</p>
        </div>

        <div v-else style="display: flex; flex-direction: column; gap: 1.25rem;">
          <!-- Metadata Group -->
          <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
            <div class="form-group" style="margin-bottom: 0;">
              <label>Agent Identifier</label>
              <input type="text" v-model="formData.agent_id" disabled />
            </div>
            <div class="form-group" style="margin-bottom: 0;">
              <label>Version (SemVer)</label>
              <input type="text" v-model="formData.version" @input="updateYamlFromForm" />
            </div>
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label>Description</label>
            <input type="text" v-model="formData.description" @input="updateYamlFromForm" />
          </div>

          <!-- Approved Models -->
          <div class="form-group" style="margin-bottom: 0;">
            <label>Approved Model List (comma separated)</label>
            <input type="text" v-model="tempModels" @input="updateModelsFromTemp" placeholder="e.g. google/gemma-2-9b-it:free" />
          </div>

          <!-- Guardrails Group -->
          <div class="form-group" style="margin-bottom: 0;">
            <label>Guardrail Rules</label>
            <div style="display: flex; flex-direction: column; gap: 0.6rem; margin-top: 0.35rem;">
              <div v-for="(g, idx) in formData.guardrails" :key="idx" class="flex-align">
                <input type="checkbox" v-model="g.enabled" :id="'g-'+idx" @change="updateYamlFromForm" style="width: auto; margin-right: 0.5rem;" />
                <label :for="'g-'+idx" style="text-transform: none; font-weight: 500; color: var(--text-primary); margin-bottom: 0; cursor: pointer;">
                  {{ g.name }} <span style="color: var(--text-muted); font-size: 0.75rem;">({{ g.type }})</span>
                </label>
              </div>
            </div>
          </div>

          <!-- HITL Group -->
          <div style="display: flex; flex-direction: column; gap: 0.75rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
            <h3 style="margin-bottom: 0.25rem;">Human-in-the-Loop Config</h3>
            
            <div class="flex-align">
              <input type="checkbox" v-model="formData.hitl.enabled" id="hitl-enable" @change="updateYamlFromForm" style="width: auto; margin-right: 0.5rem;" />
              <label for="hitl-enable" style="text-transform: none; font-weight: 500; color: var(--text-primary); margin-bottom: 0; cursor: pointer;">
                Enable HITL Workflow
              </label>
            </div>

            <div v-if="formData.hitl.enabled" class="form-group" style="margin-bottom: 0;">
              <div class="flex-between" style="margin-bottom: 0.25rem;">
                <label style="margin-bottom: 0;">Risk Threshold: {{ formData.hitl.threshold }}</label>
              </div>
              <input type="range" v-model.number="formData.hitl.threshold" min="0" max="1" step="0.1" @input="updateYamlFromForm" style="padding: 0; height: 6px; cursor: pointer;" />
            </div>
          </div>

          <!-- Data Retention Group -->
          <div style="display: flex; flex-direction: column; gap: 0.75rem; border-top: 1px solid var(--border-color); padding-top: 1rem;">
            <h3 style="margin-bottom: 0.25rem;">Retention & Regulatory</h3>

            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
              <div class="form-group" style="margin-bottom: 0;">
                <label>Audit Logs Retention (Days)</label>
                <input type="number" v-model.number="formData.data_retention.audit_logs_days" @input="updateYamlFromForm" />
              </div>
              <div class="form-group" style="margin-bottom: 0;">
                <label>Regulatory Framework Tags</label>
                <input type="text" v-model="tempTags" @input="updateTagsFromTemp" placeholder="e.g. NIST_AI_RMF, GDPR" />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Side: YAML Editor -->
      <div class="card" style="display: flex; flex-direction: column; justify-content: space-between;">
        <div>
          <div class="flex-between" style="border-bottom: 1px solid var(--border-color); padding-bottom: 0.75rem; margin-bottom: 1.5rem;">
            <h2 style="margin-bottom: 0;">YAML Policy Code (policy.yaml)</h2>
            <span class="badge badge-hitl" style="font-family: var(--font-mono); font-size: 0.7rem;">Git-Tracked File</span>
          </div>

          <p style="font-size: 0.8rem; margin-bottom: 1rem; color: var(--text-muted);">
            Direct editing here parses in real time and updates the structured form fields.
          </p>

          <textarea 
            class="code-editor" 
            v-model="rawYaml" 
            @input="updateFormFromYaml"
            placeholder="Loading yaml policy..."
            :disabled="loadingPolicy"
          ></textarea>
        </div>

        <div class="flex-between" style="margin-top: 1.5rem; border-top: 1px solid var(--border-color); padding-top: 1.5rem;">
          <span style="font-size: 0.8rem; color: var(--text-muted);">
            Active SHA: <span style="font-family: var(--font-mono); color: var(--text-secondary);">{{ activeSha.slice(0, 10) }}</span>
          </span>
          <button 
            class="btn btn-primary flex-align" 
            @click="deployPolicy" 
            :disabled="loadingPolicy || deploying"
          >
            <RefreshCw v-if="deploying" class="loading-pulse" size="14" />
            <ShieldAlert v-else size="14" />
            Simulate Git Push (Deploy)
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ShieldCheck, ShieldAlert, RefreshCw, AlertOctagon } from '@lucide/vue';
import * as yaml from 'js-yaml'; // Wait! We should check if js-yaml is imported. In single-page scripts, we can install js-yaml or implement simple parsing. Since we installed vite, we can import js-yaml if it is installed, or we can install js-yaml in the project dependencies!
// Wait! Let's check if we installed js-yaml. We did not install js-yaml. Let's make sure js-yaml is installed in frontend, or install it now. Let's install js-yaml in frontend!

export default {
  name: 'PoliciesView',
  components: {
    ShieldCheck,
    ShieldAlert,
    RefreshCw,
    AlertOctagon
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
      loadingPolicy: false,
      deploying: false,
      activeSha: 'unknown',
      rawYaml: '',
      tempModels: '',
      tempTags: '',
      formData: {
        agent_id: '',
        version: '',
        description: '',
        approved_models: [],
        allowed_tools: [],
        guardrails: [],
        hitl: { enabled: false, threshold: 0.7, rules: [] },
        data_retention: { audit_logs_days: 90, pii_masking: true },
        regulatory_frameworks: []
      },
      deployStatus: {
        success: false,
        message: '',
        errors: []
      }
    };
  },
  created() {
    this.loadActivePolicy();
  },
  methods: {
    async loadActivePolicy() {
      this.loadingPolicy = true;
      this.deployStatus.message = '';
      try {
        const res = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/policy?version=runtime`);
        if (res.ok) {
          const data = await res.json();
          this.rawYaml = data.policy_yaml;
          this.activeSha = data.commit_sha || 'unknown';
          
          // Parse YAML to initialize the form
          this.parseYamlToForm();
        }
      } catch (err) {
        console.error('Failed to load active policy:', err);
      } finally {
        this.loadingPolicy = false;
      }
    },
    parseYamlToForm() {
      try {
        const doc = yaml.load(this.rawYaml);
        if (doc && typeof doc === 'object') {
          this.formData.agent_id = doc.agent_id || '';
          this.formData.version = doc.version || '';
          this.formData.description = doc.description || '';
          this.formData.approved_models = doc.approved_models || [];
          this.formData.allowed_tools = doc.allowed_tools || [];
          this.formData.guardrails = doc.guardrails || [];
          
          // HITL
          this.formData.hitl.enabled = doc.hitl?.enabled ?? false;
          this.formData.hitl.threshold = doc.hitl?.threshold ?? 0.7;
          this.formData.hitl.rules = doc.hitl?.rules || [];
          
          // Retention
          this.formData.data_retention.audit_logs_days = doc.data_retention?.audit_logs_days ?? 90;
          this.formData.data_retention.pii_masking = doc.data_retention?.pii_masking ?? true;
          
          this.formData.regulatory_frameworks = doc.regulatory_frameworks || [];
          
          // Sync temp strings
          this.tempModels = this.formData.approved_models.join(', ');
          this.tempTags = this.formData.regulatory_frameworks.join(', ');
        }
      } catch (e) {
        // Silent catch for syntax typing
      }
    },
    updateYamlFromForm() {
      try {
        const obj = {
          agent_id: this.formData.agent_id,
          version: this.formData.version,
          description: this.formData.description,
          approved_models: this.formData.approved_models,
          allowed_tools: this.formData.allowed_tools,
          guardrails: this.formData.guardrails,
          hitl: {
            enabled: this.formData.hitl.enabled,
            threshold: this.formData.hitl.threshold,
            rules: this.formData.hitl.rules
          },
          data_retention: {
            audit_logs_days: this.formData.data_retention.audit_logs_days,
            pii_masking: this.formData.data_retention.pii_masking
          },
          regulatory_frameworks: this.formData.regulatory_frameworks
        };
        this.rawYaml = yaml.dump(obj, { noRefs: true, lineWidth: -1 });
      } catch (e) {
        console.error('Error generating YAML:', e);
      }
    },
    updateFormFromYaml() {
      this.parseYamlToForm();
    },
    updateModelsFromTemp() {
      this.formData.approved_models = this.tempModels.split(',').map(s => s.trim()).filter(Boolean);
      this.updateYamlFromForm();
    },
    updateTagsFromTemp() {
      this.formData.regulatory_frameworks = this.tempTags.split(',').map(s => s.trim()).filter(Boolean);
      this.updateYamlFromForm();
    },
    async deployPolicy() {
      this.deploying = true;
      this.deployStatus.message = '';
      this.deployStatus.errors = [];
      
      const newSha = 'commit-' + Math.random().toString(36).substr(2, 9) + Math.random().toString(36).substr(2, 9);
      
      try {
        const payload = {
          agent_id: this.selectedAgent,
          commit_sha: newSha,
          policy_yaml: this.rawYaml
        };
        
        const res = await fetch(`${this.backendUrl}/api/policies/deploy`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Deploy-Token': 'dev-token-12345'
          },
          body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (res.ok) {
          this.deployStatus.success = true;
          this.deployStatus.message = `Successfully pushed to Git. CI build passed. Active version updated to v${this.formData.version} (${newSha.slice(0,10)}).`;
          this.activeSha = newSha;
          this.$emit('policy-updated');
        } else {
          this.deployStatus.success = false;
          // Capture Pydantic validation errors
          if (data.detail && typeof data.detail === 'string') {
            this.deployStatus.message = data.detail;
          } else if (data.detail && data.detail.reason) {
            this.deployStatus.message = data.detail.reason;
          } else {
            this.deployStatus.message = 'Schema validation checks failed. Deploy rejected.';
          }
          
          if (data.detail && typeof data.detail === 'object' && data.detail.errors) {
            this.deployStatus.errors = data.detail.errors.map(e => `Field [${e.loc.join('->')}]: ${e.msg}`);
          }
        }
      } catch (err) {
        this.deployStatus.success = false;
        this.deployStatus.message = `Deploy connection error: ${err.message}`;
      } finally {
        this.deploying = false;
      }
    }
  }
};
</script>
