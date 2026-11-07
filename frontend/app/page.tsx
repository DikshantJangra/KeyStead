'use client';

import React, { useState } from 'react';
import Navbar from '../components/Navbar';
import Hero from '../components/Hero';
import ChatSimulator from '../components/ChatSimulator';
import ConnectorStore from '../components/ConnectorStore';
import PolicyPlayground from '../components/PolicyPlayground';
import DitherBackground from '../components/DitherBackground';
import { 
  FiShield, 
  FiTerminal, 
  FiCheckCircle, 
  FiKey, 
  FiAlertTriangle, 
  FiCopy, 
  FiCheck,
  FiLock,
  FiLayers,
  FiCode
} from 'react-icons/fi';
import { SiGithub, SiPython, SiDocker, SiCloudflare } from 'react-icons/si';

export default function Home() {
  const [copiedInit, setCopiedInit] = useState(false);

  const copyInit = () => {
    navigator.clipboard.writeText('uv run keystead init && uv run keystead run');
    setCopiedInit(true);
    setTimeout(() => setCopiedInit(false), 2000);
  };

  return (
    <main className="min-h-screen bg-[#fbfbfd] text-zinc-900 flex flex-col relative selection:bg-zinc-900 selection:text-white">
      {/* Animated Dither Canvas Background */}
      <DitherBackground />

      {/* Navigation Header */}
      <Navbar />

      {/* Hero Section */}
      <Hero />

      {/* Switch Room Chat Simulator */}
      <ChatSimulator />

      {/* App Store & Connectors Catalog */}
      <ConnectorStore />

      {/* Deterministic Policy Playground */}
      <PolicyPlayground />

      {/* Security Threat Matrix */}
      <section id="threat-matrix" className="py-20 border-t border-zinc-200/90 bg-[#fafafc] relative scroll-mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-10 text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-zinc-100 text-zinc-700 border border-zinc-200 mb-3">
              <FiShield className="w-3.5 h-3.5 text-zinc-500" />
              <span>CRYPTOGRAPHIC THREAT MATRIX</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
              Defenses Against Every Attack Vector
            </h2>
            <p className="mt-1.5 text-zinc-600 text-xs sm:text-sm">
              The side holding client credentials runs zero language models. Every threat is stopped deterministically.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {[
              {
                threat: 'Prompt Injection on Key-Holder',
                defense: 'The gate has NO LLM. It parses pure JSON and evaluates YAML rules.',
                badge: 'Zero-LLM Gate'
              },
              {
                threat: 'Agency Agent Hijacked',
                defense: 'Default-deny policy blocks unlisted actions; client sees the card before approving.',
                badge: 'Default Deny'
              },
              {
                threat: 'Agent Types "approve KS-0001"',
                defense: 'Only verified human participant IDs count. Agent approvals fail instantly.',
                badge: 'Identity Pinning'
              },
              {
                threat: 'Client Display Name Spoofing',
                defense: 'Sender IDs are pinned on first greeting. Different ID using same name is rejected.',
                badge: 'ID Binding'
              },
              {
                threat: 'Proposal Swapped Post-Approval',
                defense: 'Proposals are immutable in SQLite; approval is bound to SHA-256 payload_hash.',
                badge: 'SHA-256 Hash'
              },
              {
                threat: 'Replay of Expired Approval',
                defense: 'Each proposal has a 30-minute TTL and atomic CAS execution once only.',
                badge: 'Atomic CAS'
              },
              {
                threat: 'Secret Leak in Chat or Logs',
                defense: 'AES-256-GCM vault; automatic string and pattern redaction on all outbound messages.',
                badge: 'Vault Redaction'
              },
              {
                threat: 'Switch "On Behalf Of" Spoof',
                defense: 'Messages with sender_kind: platform or on_behalf_of are strictly rejected.',
                badge: 'Protocol Guard'
              },
              {
                threat: 'Ledger Manipulation',
                defense: 'Tamper-evident SHA-256 hash chain. keystead audit verify detects any alteration.',
                badge: 'Hash Ledger'
              }
            ].map((item, idx) => (
              <div 
                key={idx} 
                className="p-5 rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 transition-all flex flex-col justify-between shadow-xs"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">
                      Vector #{idx + 1}
                    </span>
                    <span className="text-[10px] font-mono font-medium text-zinc-800 bg-zinc-100 border border-zinc-200 px-2 py-0.5 rounded">
                      {item.badge}
                    </span>
                  </div>
                  <h3 className="text-xs sm:text-sm font-semibold text-zinc-900 mb-1 flex items-center gap-1.5">
                    <FiAlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    {item.threat}
                  </h3>
                  <p className="text-xs text-zinc-600 mt-1.5 leading-relaxed">
                    {item.defense}
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-zinc-100 flex items-center gap-1 text-[11px] text-zinc-700 font-mono">
                  <FiCheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Enforced Fail-Closed</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Quickstart & CLI Guide */}
      <section id="quickstart" className="py-20 border-t border-zinc-200/90 bg-white relative scroll-mt-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h2 className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">10-Minute Setup Guide</h2>
            <p className="mt-1.5 text-zinc-600 text-xs sm:text-sm">Deploy Keystead on the client machine and connect to Switch Console.</p>
          </div>

          <div className="p-5 rounded-2xl border border-zinc-200 bg-[#fbfbfd] space-y-3 font-mono text-xs shadow-xs">
            <div className="flex items-center justify-between pb-3 border-b border-zinc-200 text-zinc-600">
              <span className="font-semibold text-zinc-800">Terminal Setup</span>
              <button
                onClick={copyInit}
                className="px-2.5 py-1 rounded bg-zinc-900 hover:bg-zinc-800 text-white flex items-center gap-1.5 transition-colors shadow-xs"
              >
                {copiedInit ? <FiCheck className="w-3.5 h-3.5 text-emerald-400" /> : <FiCopy className="w-3.5 h-3.5" />}
                <span>{copiedInit ? 'Copied' : 'Copy Commands'}</span>
              </button>
            </div>

            <pre className="text-zinc-800 overflow-x-auto leading-relaxed py-1">
{`# 1. Clone & install
git clone https://github.com/DikshantJangra/KeyStead.git && cd KeyStead
uv sync

# 2. Initialize configuration and AES-256 master key
uv run keystead init

# 3. Store client credentials securely in vault
uv run keystead secret set cloudflare_token

# 4. Register gate as always-on agent in Switch Console
uv run keystead register

# 5. Run the gate
uv run keystead run`}
            </pre>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto py-8 border-t border-zinc-200 bg-white text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <FiKey className="w-4 h-4 text-zinc-700" />
            <span className="font-semibold text-zinc-900">KeyStead</span>
            <span>— Where the keys stay.</span>
          </div>
          <div>
            <span>Open Source under Apache-2.0 License. Built on Switch Protocol.</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
