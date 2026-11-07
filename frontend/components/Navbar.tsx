'use client';

import React, { useState } from 'react';
import { 
  FiKey, 
  FiMenu, 
  FiX, 
  FiTerminal, 
  FiArrowRight 
} from 'react-icons/fi';

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-200/80 bg-[#fbfbfd]/95 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <a href="#" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-zinc-900 text-white flex items-center justify-center transition-transform group-hover:scale-105">
                <FiKey className="w-4 h-4 text-zinc-100" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-base tracking-tight text-zinc-900">
                    KeyStead
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-100 text-zinc-600 border border-zinc-200">
                    v1.0
                  </span>
                </div>
                <span className="text-[9px] text-zinc-500 font-mono tracking-wider uppercase">
                  Zero-LLM Gateway
                </span>
              </div>
            </a>
          </div>

          {/* Desktop Navigation Links - Clean, non-messy */}
          <nav className="hidden md:flex items-center gap-8 text-xs font-medium text-zinc-600">
            <a href="#architecture" className="hover:text-zinc-900 transition-colors">
              Architecture
            </a>
            <a href="#simulator" className="hover:text-zinc-900 transition-colors">
              Simulator
            </a>
            <a href="#app-store" className="hover:text-zinc-900 transition-colors">
              App Store
            </a>
            <a href="#policy-engine" className="hover:text-zinc-900 transition-colors">
              Policy Engine
            </a>
            <a href="#threat-matrix" className="hover:text-zinc-900 transition-colors">
              Threat Matrix
            </a>
            <a href="#quickstart" className="hover:text-zinc-900 transition-colors">
              Setup
            </a>
          </nav>

          {/* Right Action Button - Clean without clutter badges */}
          <div className="hidden lg:flex items-center gap-3">
            <a
              href="#quickstart"
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-zinc-900 hover:bg-zinc-800 text-white shadow-xs transition-colors"
            >
              <FiTerminal className="w-3.5 h-3.5" />
              <span>Get Started</span>
            </a>
          </div>

          {/* Mobile menu trigger */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100 transition-colors"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <FiX className="w-5 h-5" /> : <FiMenu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-zinc-200 bg-white px-4 pt-3 pb-6 space-y-2">
          <a
            href="#architecture"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Architecture
          </a>
          <a
            href="#simulator"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Simulator
          </a>
          <a
            href="#app-store"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-semibold text-zinc-900 hover:bg-zinc-50"
          >
            App Store & Connectors
          </a>
          <a
            href="#policy-engine"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Policy Engine
          </a>
          <a
            href="#threat-matrix"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Threat Matrix
          </a>
          <a
            href="#quickstart"
            onClick={() => setMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-md text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            Setup Guide
          </a>
          <div className="pt-2 border-t border-zinc-100">
            <a
              href="#quickstart"
              onClick={() => setMobileMenuOpen(false)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold bg-zinc-900 text-white"
            >
              <FiTerminal className="w-3.5 h-3.5" />
              <span>Get Started</span>
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
