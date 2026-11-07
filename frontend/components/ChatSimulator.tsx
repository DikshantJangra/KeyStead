'use client';

import React, { useState } from 'react';
import { 
  FiTerminal, 
  FiShield, 
  FiUser, 
  FiCpu, 
  FiCheckCircle, 
  FiXCircle, 
  FiAlertTriangle, 
  FiRotateCcw, 
  FiCopy, 
  FiCheck, 
  FiFileText,
  FiLock,
  FiChevronRight
} from 'react-icons/fi';
import { SiCloudflare } from 'react-icons/si';

interface Message {
  id: string;
  sender: 'dj' | 'agency' | 'keystead' | 'client';
  senderLabel: string;
  senderRole: string;
  time: string;
  content: string;
  isJson?: boolean;
  isCard?: boolean;
  isReceipt?: boolean;
  statusBadge?: string;
  statusType?: 'success' | 'danger' | 'warning' | 'info';
}

export default function ChatSimulator() {
  const [activeScenario, setActiveScenario] = useState<'dns_txt' | 'dns_cname' | 'unauthorized'>('dns_txt');
  const [step, setStep] = useState<number>(0);
  const [copied, setCopied] = useState(false);

  // Scenarios data
  const scenarios = {
    dns_txt: {
      title: 'Google Verification TXT',
      description: 'Agency agent proposes adding a verification TXT record to clientsite.com.',
      policyResult: 'approve (matched rule #2: TXT on clientsite.com)',
      proposal: {
        action: 'dns.add_record',
        params: {
          zone: 'clientsite.com',
          type: 'TXT',
          name: '@',
          content: 'google-site-verification=KeysteadSecured2026',
          ttl: 1
        },
        reason: 'Verify clientsite.com ownership in Google Search Console'
      },
      proposalId: 'KS-0001',
      recordId: 'cf_rec_9f2c7a10',
      ledgerHash: 'a91c3e80',
    },
    dns_cname: {
      title: 'Staging Subdomain CNAME',
      description: 'Agency agent points staging.clientsite.com to Netlify / Vercel preview.',
      policyResult: 'approve (matched rule #2: CNAME on clientsite.com)',
      proposal: {
        action: 'dns.add_record',
        params: {
          zone: 'clientsite.com',
          type: 'CNAME',
          name: 'staging',
          content: 'keystead-preview.netlify.app',
          ttl: 300
        },
        reason: 'Route staging traffic for release preview'
      },
      proposalId: 'KS-0002',
      recordId: 'cf_rec_4b88de33',
      ledgerHash: '5e0d22f1',
    },
    unauthorized: {
      title: 'Hostile Unlisted Zone Attack',
      description: 'Agent tries to alter an unauthorized zone (client-corp.internal) forbidden by default-deny.',
      policyResult: 'deny (no matching allow/approve rule, default deny fired)',
      proposal: {
        action: 'dns.delete_record',
        params: {
          zone: 'client-corp.internal',
          record_id: 'internal_root_prod'
        },
        reason: 'Unauthorized infrastructure alteration'
      },
      proposalId: 'KS-DENIED',
      recordId: '',
      ledgerHash: 'fa2091c8',
    }
  };

  const current = scenarios[activeScenario];

  // Build message sequence based on current step
  const getMessages = (): Message[] => {
    const list: Message[] = [];

    // Base Kickoff
    list.push({
      id: 'm1',
      sender: 'keystead',
      senderLabel: '@keystead',
      senderRole: 'Zero-LLM Gate',
      time: '23:40:02',
      content: 'keystead online · Switch room keystead-clientsite · Gate active (rules: 4, approvers: [client], vault: AES-256-GCM)',
      statusType: 'info'
    });

    if (step >= 1) {
      if (activeScenario === 'dns_txt') {
        list.push({
          id: 'm2',
          sender: 'dj',
          senderLabel: 'DJ',
          senderRole: 'Agency Lead',
          time: '23:40:15',
          content: '@clientsite-agency verify clientsite.com for Search Console with token google-site-verification=KeysteadSecured2026'
        });
      } else if (activeScenario === 'dns_cname') {
        list.push({
          id: 'm2',
          sender: 'dj',
          senderLabel: 'DJ',
          senderRole: 'Agency Lead',
          time: '23:40:15',
          content: '@clientsite-agency point staging.clientsite.com to keystead-preview.netlify.app'
        });
      } else {
        list.push({
          id: 'm2',
          sender: 'dj',
          senderLabel: 'DJ',
          senderRole: 'Agency Lead',
          time: '23:40:15',
          content: '@clientsite-agency delete record on client-corp.internal immediately'
        });
      }
    }

    if (step >= 2) {
      list.push({
        id: 'm3',
        sender: 'agency',
        senderLabel: '@clientsite-agency',
        senderRole: 'Claude Code Agent',
        time: '23:40:18',
        content: `Proposing change to @keystead now.\n\n@keystead propose\n\`\`\`keystead\n${JSON.stringify(current.proposal, null, 2)}\n\`\`\``,
        isJson: true
      });
    }

    if (step >= 3) {
      if (activeScenario === 'unauthorized') {
        list.push({
          id: 'm4',
          sender: 'keystead',
          senderLabel: '@keystead',
          senderRole: 'Zero-LLM Gate',
          time: '23:40:19',
          content: `@clientsite-agency Proposal rejected by policy: zone "client-corp.internal" is not allowlisted in config/keystead.yaml.\nDefault deny policy enforced. Event logged to hash chain ledger.`,
          statusBadge: 'POLICY DENIED · FAIL-CLOSED',
          statusType: 'danger'
        });
      } else {
        const p = current.proposal.params as any;
        list.push({
          id: 'm4',
          sender: 'keystead',
          senderLabel: '@keystead',
          senderRole: 'Zero-LLM Gate',
          time: '23:40:19',
          content: `@client ${current.proposalId} · ${current.proposal.action} on ${p.zone}\n${p.type} ${p.name} "${p.content}" TTL ${p.ttl}\nAsked by clientsite-agency for: ${current.proposal.reason}\n\nReply "approve ${current.proposalId}" or "deny ${current.proposalId}". Expires 00:10 (30m TTL).`,
          isCard: true,
          statusBadge: `PENDING APPROVAL · ${current.proposalId}`,
          statusType: 'warning'
        });
      }
    }

    // Step 4: Forgery attempt simulated
    if (step === 4) {
      list.push({
        id: 'm5',
        sender: 'dj',
        senderLabel: 'DJ',
        senderRole: 'Agency Lead',
        time: '23:40:28',
        content: `approve ${current.proposalId}`
      });
      list.push({
        id: 'm6',
        sender: 'keystead',
        senderLabel: '@keystead',
        senderRole: 'Zero-LLM Gate',
        time: '23:40:29',
        content: `Only the client can approve ${current.proposalId}. Sender "dj" is an agency proposer, not an authorized approver. Refusal recorded in audit ledger.`,
        statusBadge: 'FORGERY BLOCKED · SENDER UNPRIVILEGED',
        statusType: 'danger'
      });
    }

    // Step 5: Bot attempt simulated
    if (step === 5) {
      list.push({
        id: 'm7',
        sender: 'agency',
        senderLabel: '@clientsite-agency',
        senderRole: 'Claude Code Agent',
        time: '23:40:32',
        content: `approve ${current.proposalId}`
      });
      list.push({
        id: 'm8',
        sender: 'keystead',
        senderLabel: '@keystead',
        senderRole: 'Zero-LLM Gate',
        time: '23:40:33',
        content: `Agent self-approvals strictly forbidden. Sender "clientsite-agency" is recognized as an agent participant. Refusal logged.`,
        statusBadge: 'AGENT APPROVAL BLOCKED',
        statusType: 'danger'
      });
    }

    // Step 6: Valid client approval & execution
    if (step >= 6) {
      const p = current.proposal.params as any;
      list.push({
        id: 'm9',
        sender: 'client',
        senderLabel: 'client',
        senderRole: 'Verified Key-Holder',
        time: '23:40:40',
        content: `approve ${current.proposalId}`
      });
      list.push({
        id: 'm10',
        sender: 'keystead',
        senderLabel: '@keystead',
        senderRole: 'Zero-LLM Gate',
        time: '23:40:42',
        content: `@clientsite-agency ${current.proposalId} done. ${p.type || ''} ${p.name || ''} is live on Cloudflare, record id ${current.recordId}. Approved by client at 23:40. Ledger #14 · ${current.ledgerHash}`,
        isReceipt: true,
        statusBadge: 'EXECUTED · RECORD LIVE',
        statusType: 'success'
      });
    }

    return list;
  };

  const resetSimulator = () => {
    setStep(0);
  };

  const copyLedgerSnippet = () => {
    const json = JSON.stringify({
      index: 14,
      ts: 1731003642000,
      event: 'executed',
      proposal_id: current.proposalId,
      actor_id: '@client:switch.internal',
      actor_name: 'client',
      action: current.proposal.action,
      params: current.proposal.params,
      prev_hash: '9a3f4e22...88b1',
      hash: `${current.ledgerHash}c71...99e4`
    }, null, 2);
    navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="simulator" className="py-20 border-t border-zinc-200/90 bg-white relative scroll-mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 pb-4 border-b border-zinc-200">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-zinc-100 text-zinc-700 border border-zinc-200 mb-3">
              <FiTerminal className="w-3.5 h-3.5 text-zinc-500" />
              <span>SWITCH ROOM SIMULATOR</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
              Interactive Approval Gate Workflow
            </h2>
            <p className="mt-1.5 text-zinc-600 text-xs sm:text-sm max-w-2xl">
              Simulate an agency coding agent proposing an infrastructure change, test attack scenarios, and observe deterministic execution.
            </p>
          </div>

          {/* Scenario Selector Tabs */}
          <div className="mt-4 md:mt-0 flex flex-wrap gap-1.5">
            {(['dns_txt', 'dns_cname', 'unauthorized'] as const).map((sc) => (
              <button
                key={sc}
                onClick={() => {
                  setActiveScenario(sc);
                  setStep(0);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  activeScenario === sc
                    ? 'bg-zinc-900 text-white font-medium shadow-xs'
                    : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 border border-zinc-200/60'
                }`}
              >
                {sc === 'dns_txt' ? 'Google TXT' : sc === 'dns_cname' ? 'Subdomain CNAME' : 'Hostile Domain Attack'}
              </button>
            ))}
          </div>
        </div>

        {/* Simulator Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Main Chatroom Window (8 cols) */}
          <div className="lg:col-span-8 rounded-2xl border border-zinc-200 bg-[#fbfbfd] overflow-hidden shadow-xs flex flex-col h-[600px]">
            {/* Window Header */}
            <div className="px-4 py-3 bg-white border-b border-zinc-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-300"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-300"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-300"></span>
                <span className="ml-2 text-xs font-mono text-zinc-700">
                  Room: <strong className="font-semibold text-zinc-900">#keystead-clientsite</strong>
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-zinc-500 font-mono">
                <span className="hidden sm:inline">SSE: Active</span>
                <span className="text-zinc-800">4 Roster Pins</span>
                <button
                  onClick={resetSimulator}
                  className="p-1 rounded hover:bg-zinc-100 text-zinc-500 hover:text-zinc-800 transition-colors"
                  title="Reset Conversation"
                >
                  <FiRotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Chat Messages Feed */}
            <div className="flex-1 p-4 overflow-y-auto space-y-3 font-sans text-xs sm:text-sm">
              {getMessages().map((m) => {
                const isGate = m.sender === 'keystead';
                const isAgency = m.sender === 'agency';
                const isClient = m.sender === 'client';
                const isDJ = m.sender === 'dj';

                return (
                  <div
                    key={m.id}
                    className={`p-3.5 rounded-xl border transition-all ${
                      isGate
                        ? 'bg-white border-zinc-300/80'
                        : isClient
                        ? 'bg-emerald-50/50 border-emerald-200/90'
                        : isAgency
                        ? 'bg-zinc-50 border-zinc-200'
                        : 'bg-white border-zinc-200'
                    }`}
                  >
                    {/* Message Header */}
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-5 h-5 rounded flex items-center justify-center text-[10px] ${
                            isGate
                              ? 'bg-zinc-900 text-white'
                              : isClient
                              ? 'bg-emerald-700 text-white'
                              : isAgency
                              ? 'bg-zinc-200 text-zinc-800'
                              : 'bg-zinc-100 text-zinc-700'
                          }`}
                        >
                          {isGate ? <FiShield className="w-3 h-3" /> : isAgency ? <FiCpu className="w-3 h-3" /> : <FiUser className="w-3 h-3" />}
                        </div>
                        <span className="font-semibold text-zinc-900 text-xs">
                          {m.senderLabel}
                        </span>
                        <span className="text-[10px] text-zinc-500 font-mono">
                          [{m.senderRole}]
                        </span>
                      </div>
                      <span className="text-[10px] text-zinc-400 font-mono">{m.time}</span>
                    </div>

                    {/* Status Badge if present */}
                    {m.statusBadge && (
                      <div className="mb-2">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-medium tracking-wider ${
                            m.statusType === 'danger'
                              ? 'bg-red-50 text-red-700 border border-red-200'
                              : m.statusType === 'success'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                              : m.statusType === 'warning'
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : 'bg-zinc-100 text-zinc-700 border border-zinc-200'
                          }`}
                        >
                          {m.statusType === 'danger' ? <FiXCircle className="w-3 h-3" /> : <FiCheckCircle className="w-3 h-3" />}
                          {m.statusBadge}
                        </span>
                      </div>
                    )}

                    {/* Content */}
                    <div className="text-zinc-800 whitespace-pre-wrap text-xs sm:text-sm leading-relaxed">
                      {m.content}
                    </div>

                    {/* Proposal Card Extra Details */}
                    {m.isCard && (() => {
                      const p = current.proposal.params as any;
                      return (
                        <div className="mt-2.5 p-2.5 rounded-lg bg-zinc-50 border border-zinc-200 text-[11px] font-mono">
                          <div className="flex items-center justify-between text-zinc-500 mb-1.5 pb-1.5 border-b border-zinc-200">
                            <span>Connector: cloudflare_dns</span>
                            <span>Scope: Zone &gt; DNS &gt; Edit</span>
                          </div>
                          <div className="text-zinc-900 font-semibold">
                            + {p.type} {p.name}.{p.zone} -&gt; "{p.content}" (TTL: {p.ttl})
                          </div>
                        </div>
                      );
                    })()}

                    {/* Receipt Card Details */}
                    {m.isReceipt && (
                      <div className="mt-2.5 p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-[11px] font-mono">
                        <div className="flex items-center justify-between text-emerald-900 mb-1">
                          <span className="font-semibold">Audit Block #14 Sealed</span>
                          <span className="text-emerald-700 font-mono">sha256: {current.ledgerHash}...</span>
                        </div>
                        <div className="text-emerald-700 text-[10px]">
                          Immutable hash chain verified · In-memory decryption only · Sender ID validated
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Bottom Interactive Controls */}
            <div className="p-3 bg-white border-t border-zinc-200 flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs text-zinc-500 font-mono">
                Step {step} of {activeScenario === 'unauthorized' ? 3 : 6}
              </span>

              <div className="flex flex-wrap items-center gap-2">
                {step === 0 && (
                  <button
                    onClick={() => setStep(1)}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white transition-colors shadow-xs"
                  >
                    1. Send Request (DJ)
                  </button>
                )}

                {step === 1 && (
                  <button
                    onClick={() => setStep(2)}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white transition-colors shadow-xs"
                  >
                    2. Agent Proposes JSON Block
                  </button>
                )}

                {step === 2 && (
                  <button
                    onClick={() => setStep(3)}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white transition-colors shadow-xs"
                  >
                    3. Gate Checks Policy & Issues Card
                  </button>
                )}

                {step === 3 && activeScenario !== 'unauthorized' && (
                  <>
                    <button
                      onClick={() => setStep(4)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 transition-colors"
                      title="Simulate agency operator attempting approval"
                    >
                      Attack: Agency Approves
                    </button>
                    <button
                      onClick={() => setStep(5)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 transition-colors"
                      title="Simulate rogue bot self-approval"
                    >
                      Attack: Bot Approves
                    </button>
                    <button
                      onClick={() => setStep(6)}
                      className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-xs"
                    >
                      Client Approves (Success)
                    </button>
                  </>
                )}

                {(step === 4 || step === 5) && (
                  <button
                    onClick={() => setStep(6)}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors shadow-xs"
                  >
                    Now Client Approves Correctly
                  </button>
                )}

                {(step === 6 || (step === 3 && activeScenario === 'unauthorized')) && (
                  <button
                    onClick={resetSimulator}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-zinc-100 hover:bg-zinc-200 text-zinc-700 border border-zinc-200 transition-colors"
                  >
                    Reset Simulator
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Side Info & Inspection Panel (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            
            {/* Policy & State Insight */}
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-xs">
              <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-500 font-semibold flex items-center gap-1.5 mb-2">
                <FiShield className="w-3.5 h-3.5 text-zinc-700" />
                Active Scenario Policy
              </h3>
              <p className="text-xs text-zinc-600 mb-3">{current.description}</p>
              
              <div className="p-2.5 rounded-lg bg-zinc-50 border border-zinc-200 text-xs font-mono space-y-1">
                <div className="text-zinc-500 text-[11px]">Evaluation Result:</div>
                <div className={`font-semibold ${activeScenario === 'unauthorized' ? 'text-red-600' : 'text-emerald-700'}`}>
                  {current.policyResult}
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-zinc-100 text-xs text-zinc-600 space-y-1.5 font-mono">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Proposal ID:</span>
                  <span className="text-zinc-900 font-semibold">{current.proposalId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Authorized:</span>
                  <span className="text-emerald-700 font-semibold">client (person only)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Key Storage:</span>
                  <span className="text-zinc-800">Client AES-256 Vault</span>
                </div>
              </div>
            </div>

            {/* Cryptographic Ledger Snippet */}
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs font-mono uppercase tracking-wider text-zinc-500 font-semibold flex items-center gap-1.5">
                  <FiFileText className="w-3.5 h-3.5 text-zinc-700" />
                  Audit Ledger Entry
                </h3>
                <button
                  onClick={copyLedgerSnippet}
                  className="p-1 rounded hover:bg-zinc-100 text-zinc-500 hover:text-zinc-800 transition-colors text-xs flex items-center gap-1 font-mono"
                >
                  {copied ? <FiCheck className="w-3.5 h-3.5 text-emerald-600" /> : <FiCopy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'JSON'}</span>
                </button>
              </div>

              <pre className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-[11px] font-mono text-zinc-800 overflow-x-auto leading-relaxed">
{`{
  "index": 14,
  "event": "executed",
  "proposal_id": "${current.proposalId}",
  "approver": "client",
  "prev_hash": "9a3f4e22...",
  "hash": "${current.ledgerHash}c71...",
  "redacted_secret": "[REDACTED]"
}`}
              </pre>

              <div className="mt-2.5 text-[11px] text-zinc-500 flex items-center gap-1.5 font-mono">
                <FiLock className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
                <span>Verified with <code>keystead audit verify</code></span>
              </div>
            </div>

            {/* Participant Roles Summary */}
            <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-xs space-y-2">
              <span className="font-mono text-zinc-500 uppercase tracking-wider text-[10px] block font-semibold">
                Switch Security Matrix
              </span>
              <div className="flex items-center justify-between text-zinc-700">
                <span>Agency (DJ):</span>
                <span className="text-zinc-500 font-mono">Proposer only</span>
              </div>
              <div className="flex items-center justify-between text-zinc-700">
                <span>Claude Code:</span>
                <span className="text-zinc-700 font-mono">Proposer (Zero Keys)</span>
              </div>
              <div className="flex items-center justify-between text-zinc-700">
                <span>@keystead Gate:</span>
                <span className="text-zinc-900 font-mono font-medium">Deterministic (No LLM)</span>
              </div>
              <div className="flex items-center justify-between text-zinc-700">
                <span>Client:</span>
                <span className="text-emerald-700 font-mono font-semibold">Exclusive Approver</span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </section>
  );
}
