<template>
  <div>
    <div class="flex-between" style="margin-bottom: 2rem;">
      <div>
        <h1>AI Workload Playground</h1>
        <p class="subtitle" style="margin-bottom: 0;">Submit test inputs to agents and inspect runtime policy evaluations and real-time LLM executions.</p>
      </div>
      <div class="flex-align gap-sm">
        <label style="margin-bottom: 0; color: var(--text-secondary); text-transform: none; font-weight: 500;">Select Agent:</label>
        <select v-model="selectedAgent" style="width: 220px;" @change="loadAgentPolicy">
          <option value="customer-support-agent">Customer Support Agent</option>
          <option value="loan-processor-agent">Loan Processor Agent</option>
        </select>
      </div>
    </div>

    <div class="grid-2" style="align-items: flex-start;">
      <!-- Left Card: Workload parameters form -->
      <div class="card">
        <h2>Submit Query</h2>
        
        <div class="form-group">
          <label>Target LLM Model</label>
          <select v-model="selectedModel">
            <!-- Primary (Real LLMs) first -->
            <option v-for="m in primaryModels" :key="m" :value="m">
              {{ m }} (Approved - Primary)
            </option>
            <!-- Fallbacks (Mockup LLMs) second -->
            <option v-for="m in mockModels" :key="m" :value="m">
              {{ m }} (Approved - Mockup LLM)
            </option>
            <!-- Unapproved model for block verification -->
            <option value="anthropic/claude-3-opus">
              anthropic/claude-3-opus (Unapproved - Test Block)
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>Inject Tool Execution</label>
          <select v-model="selectedTool">
            <option :value="null">None (Direct Chat)</option>
            <option v-for="t in allowedTools" :key="t" :value="t">{{ t }} (Authorized)</option>
            <option value="delete_database">delete_database (Disallowed - Test Block)</option>
          </select>
        </div>

        <div class="form-group">
          <div class="flex-between">
            <label>Prompt Input</label>
            <span style="font-size: 0.75rem; color: var(--text-muted); cursor: pointer;" @click="injectTriggerPrompt">
              Inject Test Scenario
            </span>
          </div>
          <textarea 
            v-model="prompt" 
            placeholder="Type support query or enter loan application..." 
            rows="5"
            style="resize: none;"
          ></textarea>
        </div>

        <button 
          class="btn btn-primary flex-align" 
          style="width: 100%; justify-content: center;"
          @click="submitWorkload"
          :disabled="submitting || !prompt.trim()"
        >
          <Play size="14" />
          Run AI Workload
        </button>
      </div>

      <!-- Right Card: Live pipeline feedback -->
      <div class="card" style="min-height: 440px; display: flex; flex-direction: column;">
        <h2>Evaluation Pipeline</h2>

        <div v-if="!runResult && !submitting" class="empty-state" style="padding: 6rem 0; flex: 1;">
          <Cpu size="40" class="icon" />
          <p style="font-size: 0.85rem; margin-bottom: 0;">Submit a query on the left to see the governance interceptor analyze the request.</p>
        </div>

        <div v-else style="display: flex; flex-direction: column; gap: 1.5rem; flex: 1;">
          <!-- Timeline diagram -->
          <div style="display: flex; flex-direction: column; gap: 0.85rem; padding: 1rem; background-color: rgba(0,0,0,0.15); border-radius: var(--border-radius-md); border: 1px solid var(--border-color);">
            
            <!-- Step 1: Model check -->
            <div class="flex-between" style="font-size: 0.85rem;">
              <span class="flex-align">
                <ShieldCheck v-if="pipeline.model === 'passed'" size="14" style="color: var(--color-allowed);" />
                <ShieldAlert v-else-if="pipeline.model === 'failed'" size="14" style="color: var(--color-blocked);" />
                <RefreshCw v-else class="loading-pulse" size="14" />
                Model Approval Check
              </span>
              <span :class="getPipelineBadgeClass(pipeline.model)" class="badge">{{ pipeline.model.toUpperCase() }}</span>
            </div>

            <!-- Step 2: Tool check -->
            <div class="flex-between" style="font-size: 0.85rem;">
              <span class="flex-align">
                <ShieldCheck v-if="pipeline.tool === 'passed'" size="14" style="color: var(--color-allowed);" />
                <ShieldAlert v-else-if="pipeline.tool === 'failed'" size="14" style="color: var(--color-blocked);" />
                <RefreshCw v-else class="loading-pulse" size="14" />
                Tool Authorization Check
              </span>
              <span :class="getPipelineBadgeClass(pipeline.tool)" class="badge">{{ pipeline.tool.toUpperCase() }}</span>
            </div>

            <!-- Step 3: Guardrail Check -->
            <div class="flex-between" style="font-size: 0.85rem;">
              <span class="flex-align">
                <ShieldCheck v-if="pipeline.guardrail === 'passed'" size="14" style="color: var(--color-allowed);" />
                <ShieldAlert v-else-if="pipeline.guardrail === 'failed'" size="14" style="color: var(--color-blocked);" />
                <RefreshCw v-else class="loading-pulse" size="14" />
                Guardrail Content Scanner
              </span>
              <span :class="getPipelineBadgeClass(pipeline.guardrail)" class="badge">{{ pipeline.guardrail.toUpperCase() }}</span>
            </div>

            <!-- Step 4: HITL Check -->
            <div class="flex-between" style="font-size: 0.85rem;">
              <span class="flex-align">
                <ShieldCheck v-if="pipeline.hitl === 'passed'" size="14" style="color: var(--color-allowed);" />
                <ShieldAlert v-else-if="pipeline.hitl === 'hitl_paused'" size="14" style="color: var(--color-hitl);" />
                <RefreshCw v-else class="loading-pulse" size="14" />
                Human-in-the-Loop Interceptor
              </span>
              <span :class="getPipelineBadgeClass(pipeline.hitl)" class="badge">{{ pipeline.hitl === 'hitl_paused' ? 'PAUSED' : pipeline.hitl.toUpperCase() }}</span>
            </div>
          </div>

          <!-- Dynamic Results display -->
          <div style="flex: 1;">
            <!-- Blocked Alert -->
            <div v-if="runResult && runResult.status === 'BLOCKED'" class="alert alert-danger" style="margin-bottom: 0;">
              <AlertOctagon size="18" style="margin-top: 0.1rem; flex-shrink: 0;" />
              <div>
                <strong style="display: block; margin-bottom: 0.25rem;">WORKLOAD BLOCKED BY POLICY</strong>
                <span>{{ runResult.reason }}</span>
              </div>
            </div>

            <!-- Pending HITL Review inline actions -->
            <div v-else-if="runResult && runResult.status === 'PENDING_HITL'" class="alert alert-warning" style="display: flex; flex-direction: column; gap: 1rem; margin-bottom: 0;">
              <div class="flex-align" style="align-items: flex-start;">
                <UserCheck size="18" style="margin-top: 0.1rem; flex-shrink: 0;" />
                <div>
                  <strong style="display: block; margin-bottom: 0.25rem;">WORKLOAD SUSPENDED (HITL)</strong>
                  <span>{{ runResult.reason }}</span>
                </div>
              </div>
              
              <div class="flex-align gap-sm" style="align-self: flex-end;">
                <button class="btn btn-danger" @click="decideHitlInline('REJECTED')" :disabled="decidingHitl">Reject</button>
                <button class="btn btn-success" @click="decideHitlInline('APPROVED')" :disabled="decidingHitl">
                  <RefreshCw v-if="decidingHitl" class="loading-pulse" size="12" />
                  Approve & Resume
                </button>
              </div>
            </div>

            <!-- Executed Output -->
            <div v-else-if="runResult && runResult.status === 'ALLOWED'" style="display: flex; flex-direction: column; gap: 1rem;">
              <!-- Tool Executed details -->
              <div v-if="runResult.tool_result" style="padding: 0.75rem; border-radius: var(--border-radius-md); background-color: rgba(255,255,255,0.02); border: 1px solid var(--border-color); font-size: 0.8rem;">
                <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">
                  Executed Tool: <span style="font-family: var(--font-mono); color: var(--color-primary);">{{ runResult.tool_executed }}</span>
                </div>
                <pre style="font-family: var(--font-mono); color: var(--text-secondary); max-height: 120px; overflow-y: auto; font-size: 0.75rem;">{{ JSON.stringify(runResult.tool_result, null, 2) }}</pre>
              </div>

              <!-- Chat output -->
              <div style="flex: 1;">
                <label>Agent Completion Response</label>
                <div style="padding: 1rem; border-radius: var(--border-radius-md); background-color: rgba(255,255,255,0.03); border: 1px solid var(--border-color); font-size: 0.9rem; line-height: 1.6; color: var(--text-primary); max-height: 250px; overflow-y: auto;">
                  {{ runResult.llm_response }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Play, ShieldCheck, ShieldAlert, Cpu, AlertOctagon, UserCheck, RefreshCw } from '@lucide/vue';

export default {
  name: 'PlaygroundView',
  components: {
    Play,
    ShieldCheck,
    ShieldAlert,
    Cpu,
    AlertOctagon,
    UserCheck,
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
  computed: {
    primaryModels() {
      return this.approvedModels.filter(m => m.startsWith('openai/'));
    },
    mockModels() {
      return this.approvedModels.filter(m => !m.startsWith('openai/'));
    }
  },
  data() {
    return {
      selectedAgent: this.initialAgentId,
      prompt: '',
      selectedModel: '',
      selectedTool: null,
      approvedModels: [],
      allowedTools: [],
      submitting: false,
      decidingHitl: false,
      runResult: null,
      pipeline: {
        model: 'pending',
        tool: 'pending',
        guardrail: 'pending',
        hitl: 'pending'
      }
    };
  },
  created() {
    this.loadAgentPolicy();
  },
  methods: {
    async loadAgentPolicy() {
      try {
        const res = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/policy?version=runtime`);
        if (res.ok) {
          const data = await res.json();
          this.approvedModels = data.policy_json.approved_models || [];
          this.allowedTools = (data.policy_json.allowed_tools || []).map(t => t.name);
          
          // Set default model: prefer primary OpenAI models if available
          if (this.primaryModels.length > 0) {
            this.selectedModel = this.primaryModels[0];
          } else if (this.approvedModels.length > 0) {
            this.selectedModel = this.approvedModels[0];
          }
          this.selectedTool = null;
          this.prompt = '';
          this.runResult = null;
        }
      } catch (err) {
        console.error('Failed to load agent approved items:', err);
      }
    },
    injectTriggerPrompt() {
      if (this.selectedAgent === 'customer-support-agent') {
        const scenarios = [
          {
            text: "Hello, look up order balance for customer ID 12345.",
            tool: "customer_lookup"
          },
          {
            text: "Send confirmation email to user complaining that their service is broken and they want an immediate refund.",
            tool: "send_email"
          },
          {
            text: "Please look up account detail for Social Security 000-12-3456.",
            tool: "customer_lookup"
          }
        ];
        // Pick one randomly
        const pick = scenarios[Math.floor(Math.random() * scenarios.length)];
        this.prompt = pick.text;
        this.selectedTool = pick.tool;
      } else {
        const scenarios = [
          {
            text: "Inquire bureau record for loan applicant SSN 111-99-8888.",
            tool: "credit_score_check"
          },
          {
            text: "Please approve loan request LN-98317-X for $35,000 for credit score 820.",
            tool: "approve_loan"
          }
        ];
        const pick = scenarios[Math.floor(Math.random() * scenarios.length)];
        this.prompt = pick.text;
        this.selectedTool = pick.tool;
      }
    },
    async submitWorkload() {
      this.submitting = true;
      this.runResult = null;
      
      // Reset pipeline state to running
      this.pipeline.model = 'running';
      this.pipeline.tool = 'pending';
      this.pipeline.guardrail = 'pending';
      this.pipeline.hitl = 'pending';

      const payload = {
        prompt: this.prompt,
        model: this.selectedModel,
        tool: this.selectedTool,
        tool_args: this.getMockToolArgs()
      };

      try {
        const res = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        
        // Update Pipeline steps visually
        if (res.status === 200) {
          // Allowed
          this.pipeline.model = 'passed';
          this.pipeline.tool = 'passed';
          this.pipeline.guardrail = 'passed';
          this.pipeline.hitl = 'passed';
          
          this.runResult = {
            status: 'ALLOWED',
            llm_response: data.llm_response,
            tool_executed: data.tool_result ? payload.tool : null,
            tool_result: data.tool_result
          };
          this.$emit('audit-logs-updated');
        } else if (res.status === 202) {
          // PENDING_HITL
          this.pipeline.model = 'passed';
          this.pipeline.tool = 'passed';
          this.pipeline.guardrail = 'passed';
          this.pipeline.hitl = 'hitl_paused';
          
          this.runResult = {
            status: 'PENDING_HITL',
            request_id: data.request_id,
            reason: data.reason
          };
          this.$emit('audit-logs-updated');
          this.$emit('hitl-queue-updated');
        } else {
          // Blocked
          const reason = data.detail?.reason || data.detail || 'Access Denied';
          
          // Determine which step blocked
          if (reason.includes('Model')) {
            this.pipeline.model = 'failed';
            this.pipeline.tool = 'pending';
          } else if (reason.includes('Tool') || reason.includes('authorized')) {
            this.pipeline.model = 'passed';
            this.pipeline.tool = 'failed';
          } else if (reason.includes('Guardrail') || reason.includes('PII') || reason.includes('content')) {
            this.pipeline.model = 'passed';
            this.pipeline.tool = 'passed';
            this.pipeline.guardrail = 'failed';
          } else {
            this.pipeline.model = 'failed';
          }
          
          this.runResult = {
            status: 'BLOCKED',
            reason: reason
          };
          this.$emit('audit-logs-updated');
        }
      } catch (err) {
        console.error('Connection failure during run:', err);
        this.runResult = {
          status: 'BLOCKED',
          reason: `Network error connecting to policy runtime: ${err.message}`
        };
      } finally {
        this.submitting = false;
      }
    },
    getMockToolArgs() {
      if (this.selectedTool === 'customer_lookup') {
        return { customer_id: '12345' };
      }
      if (this.selectedTool === 'send_email') {
        return { recipient: 'client@example.com', subject: 'Inquiry response', body: 'This is support updating your order.' };
      }
      if (this.selectedTool === 'credit_score_check') {
        return { ssn: '111-22-3333' };
      }
      if (this.selectedTool === 'approve_loan') {
        return { amount: 35000, credit_score: 820 };
      }
      return {};
    },
    async decideHitlInline(decision) {
      this.decidingHitl = true;
      try {
        const res = await fetch(`${this.backendUrl}/api/agents/${this.selectedAgent}/hitl/${this.runResult.request_id}/decide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision: decision })
        });
        
        const data = await res.json();
        
        if (res.ok) {
          if (decision === 'APPROVED') {
            this.pipeline.hitl = 'passed';
            this.runResult = {
              status: 'ALLOWED',
              llm_response: data.llm_response,
              tool_executed: data.tool_result ? this.selectedTool : null,
              tool_result: data.tool_result
            };
          } else {
            this.pipeline.hitl = 'failed';
            this.runResult = {
              status: 'BLOCKED',
              reason: 'Workload execution was rejected by human operator.'
            };
          }
          this.$emit('audit-logs-updated');
          this.$emit('hitl-queue-updated');
        }
      } catch (err) {
        console.error('Failed to resolve HITL inline:', err);
      } finally {
        this.decidingHitl = false;
      }
    },
    getPipelineBadgeClass(status) {
      if (status === 'passed') return 'badge-allowed';
      if (status === 'failed') return 'badge-blocked';
      if (status === 'hitl_paused') return 'badge-hitl';
      if (status === 'running') return 'badge-hitl loading-pulse';
      return 'badge-neutral';
    }
  }
};
</script>
