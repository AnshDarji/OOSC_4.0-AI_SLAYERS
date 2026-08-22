import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Gavel, Info, BookOpen } from 'lucide-react';
import ExpandableSource from './ExpandableSource';

const KanoonRenderer = ({ content }) => {
  let parsed = null;
  try {
    parsed = typeof content === 'string' ? JSON.parse(content) : content;
  } catch (e) {
    // Fallback if not JSON
    return (
      <div className="prose prose-slate max-w-none text-slate-700">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
  }

  if (!parsed || (!parsed.answer && !parsed.summary)) return null;

  return (
    <div className="space-y-6">
      {/* Domain */}
      {parsed.legal_domain && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="bg-primary-50 text-primary-700 text-xs font-semibold px-3 py-1 rounded-full border border-primary-200 uppercase tracking-wider">
            {parsed.legal_domain}
          </span>
        </div>
      )}
      
      {/* Summary */}
      {parsed.summary && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <h4 className="font-semibold text-slate-800 mb-2 flex items-center gap-2">
            <BookOpen size={18} className="text-primary-600" /> Executive Summary
          </h4>
          <div className="prose prose-sm md:prose-base prose-slate max-w-none text-slate-700">
            <ReactMarkdown>{parsed.summary}</ReactMarkdown>
          </div>
        </div>
      )}
      
      {/* Detailed Answer */}
      <div>
        <h4 className="font-semibold text-slate-800 mb-3 text-lg">Detailed Analysis</h4>
        <div className="prose prose-sm md:prose-base prose-slate max-w-none text-slate-700">
          <ReactMarkdown>{parsed.answer}</ReactMarkdown>
        </div>
      </div>
      
      {/* Key Clauses */}
      {parsed.key_clauses && parsed.key_clauses.length > 0 && (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-5">
          <h4 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
            <Gavel size={18} className="text-primary-600" /> Key Provisions & Sections
          </h4>
          <ul className="list-disc pl-5 space-y-2">
            {parsed.key_clauses.map((clause, i) => (
              <li key={i} className="text-sm md:text-base text-slate-700">{clause}</li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Similar Cases */}
      {parsed.similar_cases && parsed.similar_cases.length > 0 && (
        <div className="border-t border-slate-200 pt-6">
          <h4 className="font-semibold text-slate-800 mb-3 text-lg">Relevant Precedents</h4>
          <div className="prose prose-sm md:prose-base prose-slate max-w-none text-slate-700">
            <ReactMarkdown>{parsed.similar_cases}</ReactMarkdown>
          </div>
        </div>
      )}
      
      {/* Sources */}
      {parsed.sources && parsed.sources.length > 0 && (
        <div className="border-t border-slate-200 pt-6">
          <h4 className="font-semibold text-slate-800 mb-4 text-lg">Sources & Authorities</h4>
          <div>
            {parsed.sources.map((source, idx) => (
              <ExpandableSource key={idx} source={source} />
            ))}
          </div>
        </div>
      )}
      
      {/* Disclaimer */}
      {parsed.disclaimer && (
        <div className="bg-amber-50 p-4 rounded-xl border border-amber-200 flex gap-3 mt-8">
          <Info className="text-amber-600 shrink-0 mt-0.5" size={18} />
          <p className="text-xs md:text-sm text-amber-800 leading-relaxed">
            <strong>Important Disclaimer:</strong> {parsed.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
};

export default KanoonRenderer;

