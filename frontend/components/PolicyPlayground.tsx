'use client';

import React, { useState } from 'react';
import { 
  FiCode, 
  FiShield, 
  FiSliders,
  FiCheckCircle, 
  FiAlertTriangle, 
  FiXCircle 
} from 'react-icons/fi';

interface Rule {
  id: number;
  action: string;
  conditionDescription: string;
  effect: 'allow' | 'approve' | 'deny';
  limitPerDay?: number;
}

export default function PolicyPlayground() {
  const [selectedPreset, setSelectedPreset] = useState<'standard' | 'strict_production' | 'permissive_staging'>('standard');

  const [action, setAction] = useState<string>('dns.add_record');
  const [zone, setZone] = useState<string>('clientsite.com');
  const [recordType, setRecordType] = useState<string>('TXT');
  const [name, setName] = useState<string>('@');

  const rulesets: Record<string, Rule[]> = {
    standard: [
      { id: 1, action: 'dns.list_records', conditionDescription: 'Read-only action', effect: 'allow' },
      { id: 2, action: 'dns.add_record', conditionDescription: 'zone in [clientsite.com] AND type in [TXT, CNAME]', effect: 'approve', limitPerDay: 10 },
      { id: 3, action: 'dns.delete_record', conditionDescription: 'zone in [clientsite.com]', effect: 'approve' },
      { id: 4, action: 'social.publish_post', conditionDescription: 'All verified social channels', effect: 'approve', limitPerDay: 5 },
      { id: 5, action: '*', conditionDescription: 'Catch-all wildcard', effect: 'deny' },
    ],
    strict_production: [
      { id: 1, action: 'dns.list_records', conditionDescription: 'Read-only queries', effect: 'allow' },
      { id: 2, action: 'dns.add_record', conditionDescription: 'zone == clientsite.com AND type == TXT only', effect: 'approve', limitPerDay: 2 },
      { id: 3, action: 'dns.delete_record', conditionDescription: 'All delete operations', effect: 'deny' },
      { id: 4, action: '*', conditionDescription: 'Zero-trust lockdown', effect: 'deny' },
    ],
    permissive_staging: [
      { id: 1, action: 'dns.list_records', conditionDescription: 'Read-only queries', effect: 'allow' },
      { id: 2, action: 'dns.add_record', conditionDescription: 'zone ends_with .dev OR .staging', effect: 'approve' },
      { id: 3, action: 'dns.delete_record', conditionDescription: 'zone ends_with .staging', effect: 'approve' },
      { id: 4, action: '*', conditionDescription: 'Default deny', effect: 'deny' },
    ]
  };

  const currentRules = rulesets[selectedPreset];

  const evaluateProposal = () => {
    for (const rule of currentRules) {
      if (rule.action === '*') {
        return {
          matchedRule: rule,
          effect: rule.effect,
          reason: 'Matched wildcard fallback rule. Default deny strictly enforced.'
        };
      }

      if (rule.action === action) {
        if (rule.id === 1) {
          return {
            matchedRule: rule,
            effect: rule.effect,
            reason: 'Read-only safe operation. Allowed to execute without interrupting human client.'
          };
        }

        if (action === 'dns.add_record') {
          if (selectedPreset === 'standard') {
            const zoneMatches = zone === 'clientsite.com';
            const typeMatches = recordType === 'TXT' || recordType === 'CNAME';
            if (zoneMatches && typeMatches) {
              return {
                matchedRule: rule,
                effect: rule.effect,
                reason: `Allowlisted zone "${zone}" and permitted record type "${recordType}". Dispatched to client as approval card.`
              };
            }
          } else if (selectedPreset === 'strict_production') {
            const zoneMatches = zone === 'clientsite.com';
            const typeMatches = recordType === 'TXT';
            if (zoneMatches && typeMatches) {
              return {
                matchedRule: rule,
                effect: rule.effect,
                reason: `Strict TXT record match on "${zone}". Requires human client confirmation.`
              };
            }
          } else if (selectedPreset === 'permissive_staging') {
            if (zone.endsWith('.dev') || zone.endsWith('.staging')) {
              return {
                matchedRule: rule,
                effect: rule.effect,
                reason: `Staging zone match on suffix. Dispatched for client sign-off.`
              };
            }
          }
        }

        if (action === 'dns.delete_record') {
          if (rule.effect === 'deny') {
            return {
              matchedRule: rule,
              effect: 'deny',
              reason: 'Policy explicitly denies record deletion in this profile.'
            };
          }
          if (zone === 'clientsite.com' || zone.endsWith('.staging')) {
            return {
              matchedRule: rule,
              effect: rule.effect,
              reason: 'Delete operation requires client sign-off before API invocation.'
            };
          }
        }

        if (action === 'social.publish_post') {
          return {
            matchedRule: rule,
            effect: rule.effect,
            reason: 'Social post queued for client review.'
          };
        }
      }
    }

    return {
      matchedRule: currentRules[currentRules.length - 1],
      effect: 'deny',
      reason: 'No rule matched all conditions. Default deny enforced.'
    };
  };

  const evalResult = evaluateProposal();

  return (
    <section id="policy-engine" className="py-20 border-t border-zinc-200/90 bg-white relative scroll-mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="mb-8 pb-4 border-b border-zinc-200">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-zinc-100 text-zinc-700 border border-zinc-200 mb-3">
            <FiSliders className="w-3.5 h-3.5 text-zinc-500" />
            <span>POLICY ENGINE TESTBED</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
            Deterministic Rule Evaluation
          </h2>
          <p className="mt-1.5 text-zinc-600 text-xs sm:text-sm max-w-2xl">
            Rules in <code className="text-zinc-900 font-medium">config/keystead.yaml</code> match in sequence. 
            The first matching rule wins, and anything unlisted resolves fail-closed.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left: Proposal Input Form (5 cols) */}
          <div className="lg:col-span-5 rounded-2xl border border-zinc-200 bg-[#fbfbfd] p-5 space-y-4 shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200">
              <h3 className="text-xs font-mono uppercase tracking-wider font-semibold text-zinc-700 flex items-center gap-1.5">
                <FiCode className="w-3.5 h-3.5 text-zinc-500" />
                Simulate Proposal Payload
              </h3>
              <span className="text-[10px] font-mono text-zinc-400">JSON Parameters</span>
            </div>

            {/* Profile Selector */}
            <div>
              <label className="text-[10px] font-mono text-zinc-500 block mb-1 uppercase tracking-wider">
                Select Policy Profile
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                {[
                  { id: 'standard', label: 'Default' },
                  { id: 'strict_production', label: 'Strict Prod' },
                  { id: 'permissive_staging', label: 'Staging' },
                ].map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setSelectedPreset(p.id as any)}
                    className={`px-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      selectedPreset === p.id
                        ? 'bg-zinc-900 text-white font-medium shadow-xs'
                        : 'bg-white text-zinc-600 hover:bg-zinc-100 border border-zinc-200/80'
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Action Selection */}
            <div>
              <label className="text-[10px] font-mono text-zinc-500 block mb-1 uppercase tracking-wider">
                Requested Action
              </label>
              <select
                value={action}
                onChange={(e) => setAction(e.target.value)}
                className="w-full bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-zinc-800 focus:outline-none focus:border-zinc-400"
              >
                <option value="dns.add_record">dns.add_record</option>
                <option value="dns.delete_record">dns.delete_record</option>
                <option value="dns.list_records">dns.list_records (Read-Only)</option>
                <option value="social.publish_post">social.publish_post</option>
                <option value="cloudflare.purge_cache">cloudflare.purge_cache (Unlisted)</option>
              </select>
            </div>

            {/* Zone Param */}
            <div>
              <label className="text-[10px] font-mono text-zinc-500 block mb-1 uppercase tracking-wider">
                Zone Parameter
              </label>
              <input
                type="text"
                value={zone}
                onChange={(e) => setZone(e.target.value)}
                placeholder="clientsite.com"
                className="w-full bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-zinc-800 focus:outline-none focus:border-zinc-400"
              />
            </div>

            {/* Record Type Param */}
            {action === 'dns.add_record' && (
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-mono text-zinc-500 block mb-1 uppercase tracking-wider">
                    Record Type
                  </label>
                  <select
                    value={recordType}
                    onChange={(e) => setRecordType(e.target.value)}
                    className="w-full bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-zinc-800 focus:outline-none focus:border-zinc-400"
                  >
                    <option value="TXT">TXT</option>
                    <option value="CNAME">CNAME</option>
                    <option value="A">A (IPv4)</option>
                    <option value="MX">MX</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-mono text-zinc-500 block mb-1 uppercase tracking-wider">
                    Name / Subdomain
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="@"
                    className="w-full bg-white border border-zinc-200 rounded-lg px-2.5 py-1.5 text-xs font-mono text-zinc-800 focus:outline-none focus:border-zinc-400"
                  />
                </div>
              </div>
            )}

            {/* Quick Test Templates */}
            <div className="pt-2">
              <span className="text-[10px] font-mono uppercase text-zinc-400 block mb-1">
                Quick Test Templates:
              </span>
              <div className="flex flex-wrap gap-1">
                <button
                  onClick={() => {
                    setAction('dns.add_record');
                    setZone('clientsite.com');
                    setRecordType('TXT');
                  }}
                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-white hover:bg-zinc-100 text-zinc-700 border border-zinc-200"
                >
                  Safe TXT
                </button>
                <button
                  onClick={() => {
                    setAction('dns.add_record');
                    setZone('clientsite.com');
                    setRecordType('A');
                  }}
                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-white hover:bg-zinc-100 text-zinc-700 border border-zinc-200"
                >
                  A Record (Strict)
                </button>
                <button
                  onClick={() => {
                    setAction('dns.delete_record');
                    setZone('internal-admin.net');
                  }}
                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-white hover:bg-zinc-100 text-zinc-700 border border-zinc-200"
                >
                  Foreign Zone
                </button>
              </div>
            </div>
          </div>

          {/* Right: Decision Output & Rule Hierarchy (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            
            {/* Real-time Verdict Banner */}
            <div
              className={`p-4 rounded-xl border transition-all ${
                evalResult.effect === 'allow'
                  ? 'bg-emerald-50/70 border-emerald-300'
                  : evalResult.effect === 'approve'
                  ? 'bg-amber-50/70 border-amber-300'
                  : 'bg-red-50/70 border-red-300'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-zinc-600">
                  Gate Evaluation Result
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                    evalResult.effect === 'allow'
                      ? 'bg-emerald-700 text-white'
                      : evalResult.effect === 'approve'
                      ? 'bg-amber-600 text-white'
                      : 'bg-red-700 text-white'
                  }`}
                >
                  EFFECT: {evalResult.effect}
                </span>
              </div>

              <div className="text-xs sm:text-sm font-semibold text-zinc-900 mt-1">
                {evalResult.effect === 'allow' && 'Safe Read-Only Operation: Immediate Execution'}
                {evalResult.effect === 'approve' && 'Permitted Action: Queued for Human Client Approval'}
                {evalResult.effect === 'deny' && 'Forbidden by Policy: Refused Fail-Closed (Zero Execution)'}
              </div>

              <p className="mt-1.5 text-xs text-zinc-600 font-mono leading-relaxed">
                {evalResult.reason}
              </p>
            </div>

            {/* Ordered Rule Stack */}
            <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-xs">
              <div className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-2.5 flex items-center justify-between">
                <span>Rule Hierarchy (First Match Wins)</span>
                <span className="text-zinc-700 font-semibold">Fallback: DEFAULT DENY</span>
              </div>

              <div className="space-y-1.5 font-mono text-xs">
                {currentRules.map((r, i) => {
                  const isMatched = evalResult.matchedRule.id === r.id;

                  return (
                    <div
                      key={r.id}
                      className={`p-2.5 rounded-lg border flex items-center justify-between transition-all ${
                        isMatched
                          ? 'bg-zinc-50 border-zinc-400 text-zinc-900 font-medium'
                          : 'bg-white border-zinc-200 text-zinc-400 opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className={`w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold ${
                          isMatched ? 'bg-zinc-900 text-white' : 'bg-zinc-200 text-zinc-600'
                        }`}>
                          {i + 1}
                        </span>
                        <div>
                          <span className="text-zinc-900 font-semibold">{r.action}</span>
                          <span className="text-[10px] text-zinc-500 ml-1.5">({r.conditionDescription})</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {r.limitPerDay && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">
                            max {r.limitPerDay}/day
                          </span>
                        )}
                        <span className={`px-2 py-0.2 rounded text-[10px] uppercase font-bold ${
                          r.effect === 'allow'
                            ? 'bg-emerald-100 text-emerald-800'
                            : r.effect === 'approve'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {r.effect}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-3 pt-2.5 border-t border-zinc-100 text-[10px] text-zinc-500 flex items-center justify-between font-mono">
                <span>Evaluated in Python</span>
                <span className="text-zinc-700 font-semibold">keystead/policy.py</span>
              </div>
            </div>

          </div>
        </div>
      </div>
    </section>
  );
}
