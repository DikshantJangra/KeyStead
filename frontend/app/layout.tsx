import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'KeyStead — Deterministic Security Gateway for Autonomous AI Agents',
  description: 'Your agency does the work. Your keys stay with you. A zero-LLM security gateway built on the Switch agent protocol with default-deny policies, AES-256 encrypted vault, and hash-chained audit ledgers.',
  keywords: ['KeyStead', 'AI Security', 'Agent Protocol', 'Switch Room', 'Credential Protection', 'Zero-LLM Gate', 'Cloudflare DNS', 'Audit Ledger'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="bg-[#fbfbfd] text-zinc-900 min-h-screen selection:bg-zinc-900 selection:text-white">
        {children}
      </body>
    </html>
  );
}
