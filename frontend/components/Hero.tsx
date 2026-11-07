'use client';

import React, { useState } from 'react';
import { 
  FiKey, 
  FiShield, 
  FiLock, 
  FiCheckCircle, 
  FiArrowRight, 
  FiCopy, 
  FiCheck, 
  FiTerminal, 
  FiAlertTriangle,
  FiXCircle,
  FiMinusCircle,
  FiLayers
} from 'react-icons/fi';
import { SiCloudflare, SiDocker, SiPython } from 'react-icons/si';

export default function Hero() {
  const [copied, setCopied] = useState(false);

  const copyCommand = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="relative overflow-hidden pt-12 pb-20 lg:pt-20 lg:pb-28">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Top Badges */}
        <div className="flex flex-wrap items-center justify-center gap-2.5 mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono text-zinc-700 bg-white border border-zinc-200/90 shadow-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            <span>Switch Protocol Agent v1.0</span>
          </div>

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono text-zinc-700 bg-white border border-zinc-200/90 shadow-xs">
            <FiShield className="w-3.5 h-3.5 text-zinc-600" />
            <span>Zero-LLM Gate · Immune to Prompt Injection</span>
          </div>
        </div>

        {/* Main Headline */}
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-zinc-900 leading-[1.08] text-balance">
            Your agency does the work.{' '}
            <span className="block mt-1 text-zinc-500 font-semibold">
              Your keys stay with you.
            </span>
          </h1>

          <p className="mt-6 text-base sm:text-lg text-zinc-600 max-w-2xl mx-auto leading-relaxed text-balance">
            Stop sending Cloudflare, AWS, and hosting credentials over WhatsApp. 
            <strong className="text-zinc-900 font-semibold"> Keystead</strong> lets agency AI agents 
            propose changes inside private Switch rooms, while secrets remain encrypted on the client machine. 
            Nothing executes until the client types{' '}
            <code className="px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-800 font-mono text-xs border border-zinc-200">
              approve KS-0001
            </code>.
          </p>

          {/* Action CTAs */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#simulator"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-xs sm:text-sm text-white bg-zinc-900 hover:bg-zinc-800 transition-colors shadow-xs"
            >
              <FiTerminal className="w-4 h-4" />
              <span>Try Switch Simulator</span>
              <FiArrowRight className="w-3.5 h-3.5 text-zinc-400" />
            </a>

            <a
              href="#app-store"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-xs sm:text-sm text-zinc-700 bg-white hover:bg-zinc-50 border border-zinc-200/90 transition-colors shadow-xs"
            >
              <FiKey className="w-4 h-4 text-zinc-500" />
              <span>Browse App Store</span>
            </a>
          </div>

          {/* Quickstart Command Bar */}
          <div className="mt-6 flex justify-center">
            <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-lg bg-zinc-100/80 border border-zinc-200 text-xs font-mono text-zinc-700 shadow-xs max-w-full overflow-x-auto">
              <span className="text-zinc-400 select-none">$</span>
              <span>uv run keystead init && uv run keystead run</span>
              <button
                onClick={() => copyCommand('uv run keystead init && uv run keystead run')}
                className="ml-2 p-1 rounded hover:bg-zinc-200 text-zinc-500 hover:text-zinc-800 transition-colors"
                title="Copy to clipboard"
              >
                {copied ? <FiCheck className="w-3.5 h-3.5 text-emerald-600" /> : <FiCopy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>

        {/* Visual Architecture Comparison: Traditional vs Keystead */}
        <div id="architecture" className="mt-16 grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl mx-auto scroll-mt-24">
          
          {/* Traditional Way */}
          <div className="rounded-2xl border border-zinc-200/90 bg-white p-6 flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
                <span className="text-xs font-mono font-semibold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                  <FiAlertTriangle className="w-4 h-4 text-amber-500" />
                  Traditional Agency Sharing
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">
                  Uncontrolled Scope
                </span>
              </div>

              <div className="mt-4 space-y-3 text-xs sm:text-sm text-zinc-600">
                <div className="flex items-start gap-2.5">
                  <FiMinusCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                  <span><strong>Plaintext Transmission:</strong> Passwords and API tokens sent over WhatsApp, Slack, or email persist forever in message logs.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <FiMinusCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                  <span><strong>Permanent Root Access:</strong> Agency engineers and autonomous agents retain admin access indefinitely without rotation.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <FiMinusCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                  <span><strong>Prompt Injection Hazard:</strong> If an agency AI agent gets compromised, client credentials enter the LLM context.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <FiMinusCircle className="w-4 h-4 text-red-500 mt-0.5 shrink-0" />
                  <span><strong>No Audit Trail:</strong> No verifiable record of who approved what change, when, or why.</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-zinc-100 text-[11px] text-zinc-500 font-mono">
              Vector: Permanent credentials shared with third parties
            </div>
          </div>

          {/* Keystead Architecture */}
          <div className="rounded-2xl border border-zinc-300 bg-white p-6 flex flex-col justify-between shadow-xs">
            <div>
              <div className="flex items-center justify-between pb-4 border-b border-zinc-100">
                <span className="text-xs font-mono font-semibold text-zinc-900 uppercase tracking-wider flex items-center gap-1.5">
                  <FiShield className="w-4 h-4 text-zinc-800" />
                  The Keystead Gateway Model
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-900 text-white font-medium">
                  Default Deny
                </span>
              </div>

              <div className="mt-4 space-y-3 text-xs sm:text-sm text-zinc-700">
                <div className="flex items-start gap-2.5">
                  <FiCheckCircle className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                  <span><strong>Zero-LLM on Key-Holder:</strong> The gate is pure deterministic Python. It parses JSON, matches rules, and holds zero AI surface.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <FiCheckCircle className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                  <span><strong>AES-256-GCM Vault:</strong> Secrets never leave the client machine. Ephemeral in-memory decryption strictly for execution.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <FiCheckCircle className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                  <span><strong>Strict Human-in-the-Loop:</strong> Only the pinned human approver can approve. Autonomous agent self-approvals are rejected.</span>
                </div>
                <div className="flex items-start gap-2.5">
                  <FiCheckCircle className="w-4 h-4 text-emerald-600 mt-0.5 shrink-0" />
                  <span><strong>SHA-256 Hash Chain:</strong> Every proposal, vote, and execution is sealed into an immutable audit.jsonl ledger.</span>
                </div>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-zinc-100 text-[11px] text-zinc-600 font-mono flex items-center justify-between">
              <span>Keystead Gate: Active & Pinned</span>
              <span className="text-zinc-900 font-medium">Policy: FAIL-CLOSED</span>
            </div>
          </div>
        </div>

        {/* 6-Step Workflow Summary Strip */}
        <div className="mt-12 max-w-5xl mx-auto rounded-xl bg-white border border-zinc-200/90 p-5 shadow-xs">
          <div className="text-[11px] font-mono font-semibold text-zinc-500 uppercase tracking-wider text-center mb-4">
            Six-Step Cryptographic Execution Protocol
          </div>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-center font-mono">
            {[
              { num: '01', title: 'Request', desc: 'Agency asks agent for infrastructure update' },
              { num: '02', title: 'Propose', desc: 'Agent outputs structured JSON block' },
              { num: '03', title: 'Check', desc: 'Gate evaluates policy & emits card with hash' },
              { num: '04', title: 'Approve', desc: 'Client types "approve KS-NNNN"' },
              { num: '05', title: 'Execute', desc: 'Gate executes single API call with secret' },
              { num: '06', title: 'Receipt', desc: 'Cryptographic ledger line appended' },
            ].map((st) => (
              <div key={st.num} className="p-2.5 rounded-lg bg-zinc-50 border border-zinc-100">
                <div className="text-zinc-900 font-bold text-xs">{st.num}. {st.title}</div>
                <p className="text-[10px] text-zinc-500 font-sans mt-1 leading-snug">{st.desc}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
}
