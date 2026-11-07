'use client';

import React, { useState } from 'react';
import { 
  FiGrid, 
  FiSearch, 
  FiTerminal, 
  FiCopy, 
  FiCheck, 
  FiX, 
  FiShield, 
  FiGlobe
} from 'react-icons/fi';
import { 
  SiCloudflare, 
  SiGithub, 
  SiVercel, 
  SiPostgresql, 
  SiStripe, 
  SiAmazonwebservices, 
  SiInstagram 
} from 'react-icons/si';

interface ConnectorItem {
  id: string;
  name: string;
  category: 'dns' | 'devops' | 'social' | 'database' | 'commerce';
  categoryLabel: string;
  version: string;
  badge: 'Bundled' | 'Official';
  icon: React.ReactNode;
  summary: string;
  actions: string[];
  secretName: string;
  secretScope: string;
  configYaml: string;
  isolationNote: string;
}

export default function ConnectorStore() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeConnector, setActiveConnector] = useState<ConnectorItem | null>(null);
  const [copiedYaml, setCopiedYaml] = useState(false);
  const [copiedCli, setCopiedCli] = useState(false);

  const connectors: ConnectorItem[] = [
    {
      id: 'cloudflare_dns',
      name: 'Cloudflare DNS',
      category: 'dns',
      categoryLabel: 'DNS & Infrastructure',
      version: 'v1.4.0',
      badge: 'Bundled',
      icon: <SiCloudflare className="w-5 h-5 text-orange-500" />,
      summary: 'Automate DNS record creation, deletion, and verification. Hardened with zone allowlists and auto-TTL enforcement.',
      actions: ['dns.add_record', 'dns.delete_record', 'dns.list_records'],
      secretName: 'cloudflare_token',
      secretScope: 'Zone > DNS > Edit (restricted to explicit zone IDs)',
      configYaml: `connectors:
  cloudflare_dns:
    secret: cloudflare_token
    zones: [clientsite.com, example.org]

rules:
  - action: dns.list_records
    effect: allow
  - action: dns.add_record
    when:
      zone: {in: [clientsite.com]}
      type: {in: [TXT, CNAME]}
    effect: approve
    limit_per_day: 10`,
      isolationNote: 'Token is stored in AES-256-GCM vault, decrypted only during execute(), and auto-redacted from all outgoing messages.'
    },
    {
      id: 'octodns_dns',
      name: 'OctoDNS Multi-Cloud',
      category: 'dns',
      categoryLabel: 'DNS & Infrastructure',
      version: 'v1.1.0',
      badge: 'Bundled',
      icon: <FiGlobe className="w-5 h-5 text-blue-600" />,
      summary: 'Manage AWS Route 53, NS1, Google Cloud DNS, Azure DNS, and DigitalOcean using octoDNS multi-provider drivers.',
      actions: ['dns.add_record', 'dns.delete_record', 'dns.list_records'],
      secretName: 'route53_secret',
      secretScope: 'Route53:ChangeResourceRecordSets on authorized zones only',
      configYaml: `connectors:
  octodns_dns:
    secret: route53_secret
    provider: octodns_route53.Route53Provider
    secret_kwarg: secret_access_key
    options: {access_key_id: AKIAEXAMPLE}
    zones: [clientsite.com]`,
      isolationNote: 'Uses standard octoDNS pluggable provider model. Records are normalized before policy verification.'
    },
    {
      id: 'postiz_social',
      name: 'Postiz Social Media',
      category: 'social',
      categoryLabel: 'Social & Marketing',
      version: 'v1.0.2',
      badge: 'Bundled',
      icon: <SiInstagram className="w-5 h-5 text-pink-600" />,
      summary: 'Publish verified posts to Instagram, LinkedIn, X/Twitter, and TikTok via an isolated AGPL container.',
      actions: ['social.publish_post', 'social.schedule_post'],
      secretName: 'postiz_api_key',
      secretScope: 'Postiz Workspace API Key (isolated HTTP socket)',
      configYaml: `connectors:
  postiz_social:
    secret: postiz_api_key
    base_url: http://postiz:5000/api
    integrations: [clientsite-instagram, clientsite-linkedin]

rules:
  - action: social.publish_post
    effect: approve
    limit_per_day: 5`,
      isolationNote: 'Postiz runs in a separate Docker container with no direct network route to client key storage.'
    },
    {
      id: 'github_deployments',
      name: 'GitHub Deployments & Releases',
      category: 'devops',
      categoryLabel: 'DevOps & CI/CD',
      version: 'v2.0.0',
      badge: 'Official',
      icon: <SiGithub className="w-5 h-5 text-zinc-900" />,
      summary: 'Gate production environment releases, tag creations, and repository environment variable updates behind client approval.',
      actions: ['repo.create_release', 'env.approve_deployment', 'secrets.update_repo'],
      secretName: 'github_pat',
      secretScope: 'Repo:Deployments & Environments (No write to main branch)',
      configYaml: `connectors:
  github_deployments:
    secret: github_pat
    repositories: [org/production-app]

rules:
  - action: env.approve_deployment
    when:
      environment: {in: [staging, production]}
    effect: approve`,
      isolationNote: 'Personal access tokens never leave client premises; agent cannot merge PRs or bypass branch protection rules.'
    },
    {
      id: 'aws_sts_gate',
      name: 'AWS STS Ephemeral Role Gate',
      category: 'dns',
      categoryLabel: 'DNS & Infrastructure',
      version: 'v1.2.0',
      badge: 'Official',
      icon: <SiAmazonwebservices className="w-5 h-5 text-amber-600" />,
      summary: 'Generates strictly scoped 15-minute temporary session tokens for S3 syncs or ECS tasks rather than sharing long-lived keys.',
      actions: ['aws.assume_role', 's3.sync_bucket', 'ecs.update_service'],
      secretName: 'aws_iam_master',
      secretScope: 'sts:AssumeRole with client-side session policy constraints',
      configYaml: `connectors:
  aws_sts_gate:
    secret: aws_iam_master
    role_arn: arn:aws:iam::123456789012:role/KeysteadAgentRole
    max_duration_seconds: 900`,
      isolationNote: 'Session policies restrict agent permissions down to individual S3 prefixes or task definition revisions.'
    },
    {
      id: 'stripe_billing',
      name: 'Stripe Billing & Ops',
      category: 'commerce',
      categoryLabel: 'Commerce & Payments',
      version: 'v1.0.1',
      badge: 'Official',
      icon: <SiStripe className="w-5 h-5 text-indigo-600" />,
      summary: 'Enables autonomous support agents to propose refunds, customer credit applications, or discounts with mandatory client sign-off.',
      actions: ['billing.create_coupon', 'billing.refund_charge', 'customer.verify'],
      secretName: 'stripe_restricted_key',
      secretScope: 'Restricted Key: Charges (Write), Customers (Read)',
      configYaml: `connectors:
  stripe_billing:
    secret: stripe_restricted_key
    max_refund_cents: 50000

rules:
  - action: billing.refund_charge
    effect: approve`,
      isolationNote: 'Strict transaction limit enforcement on the client gate before API transmission.'
    },
    {
      id: 'vercel_deploy',
      name: 'Vercel Project & DNS',
      category: 'devops',
      categoryLabel: 'DevOps & CI/CD',
      version: 'v1.3.0',
      badge: 'Official',
      icon: <SiVercel className="w-5 h-5 text-zinc-900" />,
      summary: 'Safeguard production custom domains and preview aliases from being pointed to unapproved deployment hashes.',
      actions: ['domain.add_alias', 'deployment.promote_prod', 'domain.verify'],
      secretName: 'vercel_token',
      secretScope: 'Projects & Domains Scope on specified Team ID',
      configYaml: `connectors:
  vercel_deploy:
    secret: vercel_token
    team_id: team_keystead
    projects: [client-web]`,
      isolationNote: 'Verifies deployment commit hashes against pinned Git tags before routing domain traffic.'
    },
    {
      id: 'postgres_broker',
      name: 'PostgreSQL / Neon Gate',
      category: 'database',
      categoryLabel: 'Databases & Storage',
      version: 'v1.0.4',
      badge: 'Official',
      icon: <SiPostgresql className="w-5 h-5 text-blue-700" />,
      summary: 'Client-side query broker allowing AI agents to inspect schemas and propose safe schema migrations without exposing DB credentials.',
      actions: ['db.run_read_query', 'db.apply_migration', 'db.describe_table'],
      secretName: 'db_connection_string',
      secretScope: 'PostgreSQL Connection with read-only fallback role',
      configYaml: `connectors:
  postgres_broker:
    secret: db_connection_string
    allowed_schemas: [public, analytics]

rules:
  - action: db.run_read_query
    effect: allow
  - action: db.apply_migration
    effect: approve`,
      isolationNote: 'All migrations execute inside dry-run transactional rollback tests before presenting the diff to the client.'
    }
  ];

  // Filtering
  const filtered = connectors.filter((c) => {
    const matchesCategory = selectedCategory === 'all' || c.category === selectedCategory;
    const matchesSearch = 
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.actions.some(a => a.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCategory && matchesSearch;
  });

  const handleCopyYaml = (yaml: string) => {
    navigator.clipboard.writeText(yaml);
    setCopiedYaml(true);
    setTimeout(() => setCopiedYaml(false), 2000);
  };

  const handleCopyCli = (secret: string) => {
    navigator.clipboard.writeText(`uv run keystead secret set ${secret}`);
    setCopiedCli(true);
    setTimeout(() => setCopiedCli(false), 2000);
  };

  return (
    <section id="app-store" className="py-20 border-t border-zinc-200/90 bg-[#fafafc] relative scroll-mt-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Heading */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 pb-4 border-b border-zinc-200">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-zinc-100 text-zinc-700 border border-zinc-200 mb-3">
              <FiGrid className="w-3.5 h-3.5 text-zinc-500" />
              <span>CONNECTOR STORE & APP CATALOG</span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-zinc-900 tracking-tight">
              Pre-built Integrations & Sandboxes
            </h2>
            <p className="mt-1.5 text-zinc-600 text-xs sm:text-sm max-w-2xl">
              Equip your Keystead gate with isolated connectors. Each integration executes within client memory boundaries and strictly adheres to local policy rules.
            </p>
          </div>

          {/* Search bar */}
          <div className="mt-4 md:mt-0 relative w-full md:w-64">
            <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 w-3.5 h-3.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter actions or apps..."
              className="w-full pl-9 pr-3 py-1.5 bg-white border border-zinc-200 rounded-lg text-xs text-zinc-800 placeholder-zinc-400 focus:outline-none focus:border-zinc-400 shadow-xs transition-colors"
            />
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 mb-8">
          {[
            { id: 'all', label: 'All Connectors' },
            { id: 'dns', label: 'DNS & Infrastructure' },
            { id: 'devops', label: 'DevOps & CI/CD' },
            { id: 'social', label: 'Social & Marketing' },
            { id: 'database', label: 'Databases' },
            { id: 'commerce', label: 'Commerce' },
          ].map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedCategory === cat.id
                  ? 'bg-zinc-900 text-white font-medium shadow-xs'
                  : 'bg-white text-zinc-600 hover:bg-zinc-100 border border-zinc-200/80'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Connectors Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-zinc-200 bg-white hover:border-zinc-300 p-5 flex flex-col justify-between transition-all group shadow-xs"
            >
              <div>
                {/* Header: Icon & Badge */}
                <div className="flex items-start justify-between mb-3.5">
                  <div className="w-10 h-10 rounded-lg bg-zinc-50 border border-zinc-200 flex items-center justify-center transition-colors">
                    {item.icon}
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">
                    {item.badge}
                  </span>
                </div>

                {/* Name & Version */}
                <h3 className="text-sm font-semibold text-zinc-900 flex items-center justify-between">
                  <span>{item.name}</span>
                  <span className="text-[10px] font-mono text-zinc-400 font-normal">{item.version}</span>
                </h3>

                <p className="mt-1.5 text-xs text-zinc-600 line-clamp-3 leading-relaxed">
                  {item.summary}
                </p>

                {/* Supported Actions Pills */}
                <div className="mt-3.5 pt-3 border-t border-zinc-100">
                  <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-wider block mb-1">
                    Actions ({item.actions.length}):
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {item.actions.map((act) => (
                      <span
                        key={act}
                        className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-50 text-zinc-600 border border-zinc-200"
                      >
                        {act}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Card Footer */}
              <div className="mt-5 pt-3 border-t border-zinc-100 flex items-center justify-between">
                <span className="text-[11px] font-mono text-zinc-500">
                  Secret: <code className="text-zinc-800 font-medium">{item.secretName}</code>
                </span>

                <button
                  onClick={() => setActiveConnector(item)}
                  className="px-2.5 py-1 rounded-md text-xs font-medium bg-zinc-900 hover:bg-zinc-800 text-white transition-colors shadow-xs"
                >
                  Configure
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Modal / Detailed Inspector */}
        {activeConnector && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-900/40 backdrop-blur-xs">
            <div className="w-full max-w-xl bg-white border border-zinc-200 rounded-2xl shadow-xl overflow-hidden flex flex-col max-h-[85vh]">
              {/* Modal Header */}
              <div className="px-5 py-4 bg-zinc-50 border-b border-zinc-200 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white border border-zinc-200 flex items-center justify-center">
                    {activeConnector.icon}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-zinc-900 flex items-center gap-2">
                      {activeConnector.name}
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-200 text-zinc-700">
                        {activeConnector.badge}
                      </span>
                    </h3>
                    <span className="text-[11px] text-zinc-500 font-mono">
                      Category: {activeConnector.categoryLabel}
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => setActiveConnector(null)}
                  className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 hover:bg-zinc-200 transition-colors"
                >
                  <FiX className="w-4 h-4" />
                </button>
              </div>

              {/* Modal Body */}
              <div className="p-5 overflow-y-auto space-y-4 text-xs sm:text-sm">
                <div>
                  <h4 className="text-[10px] font-mono uppercase text-zinc-400 tracking-wider mb-1">
                    Connector Summary
                  </h4>
                  <p className="text-zinc-600 leading-relaxed text-xs">
                    {activeConnector.summary}
                  </p>
                </div>

                {/* Secret Setup CLI */}
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-mono font-medium text-zinc-800 flex items-center gap-1.5">
                      <FiTerminal className="w-3.5 h-3.5" />
                      1. Store Vault Secret on Client Machine
                    </span>
                    <button
                      onClick={() => handleCopyCli(activeConnector.secretName)}
                      className="text-xs font-mono text-zinc-500 hover:text-zinc-900 flex items-center gap-1"
                    >
                      {copiedCli ? <FiCheck className="w-3.5 h-3.5 text-emerald-600" /> : <FiCopy className="w-3.5 h-3.5" />}
                      <span>{copiedCli ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="font-mono text-xs text-zinc-900 bg-white p-2 rounded border border-zinc-200 overflow-x-auto">
                    uv run keystead secret set {activeConnector.secretName}
                  </div>
                  <div className="mt-1.5 text-[10px] text-zinc-500 font-mono">
                    Scope: <span className="text-zinc-700">{activeConnector.secretScope}</span>
                  </div>
                </div>

                {/* YAML Configuration */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-mono uppercase text-zinc-500 tracking-wider">
                      2. Add to config/keystead.yaml
                    </span>
                    <button
                      onClick={() => handleCopyYaml(activeConnector.configYaml)}
                      className="text-xs font-mono text-zinc-500 hover:text-zinc-900 flex items-center gap-1"
                    >
                      {copiedYaml ? <FiCheck className="w-3.5 h-3.5 text-emerald-600" /> : <FiCopy className="w-3.5 h-3.5" />}
                      <span>{copiedYaml ? 'Copied YAML' : 'Copy'}</span>
                    </button>
                  </div>
                  <pre className="p-3 rounded-lg bg-zinc-900 text-zinc-100 text-[11px] font-mono overflow-x-auto leading-relaxed">
                    {activeConnector.configYaml}
                  </pre>
                </div>

                {/* Isolation Note */}
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200 text-xs text-zinc-600 flex items-start gap-2">
                  <FiShield className="w-3.5 h-3.5 text-zinc-700 mt-0.5 shrink-0" />
                  <div>
                    <strong className="text-zinc-900 font-semibold">Security Boundary: </strong>
                    {activeConnector.isolationNote}
                  </div>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="px-5 py-3 bg-zinc-50 border-t border-zinc-200 flex items-center justify-between">
                <span className="text-[11px] text-zinc-500 font-mono">
                  Default Rule: Fail-Closed
                </span>
                <button
                  onClick={() => setActiveConnector(null)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white transition-colors shadow-xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </section>
  );
}
