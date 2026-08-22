import React, { useState } from 'react';
import { ChevronRight, ChevronDown, Book, Scale, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const ExpandableSource = ({ source }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Determine Source Type and appropriate icon/label
  const docType = source.metadata?.document_type || '';
  const domain = source.legal_domain || '';
  const sourceName = source.source_name || 'Legal Source';
  
  let isJudgment = docType === 'judgment' || sourceName.toLowerCase().includes('v.');
  let isStatute = docType === 'statute' || sourceName.toLowerCase().includes('act') || sourceName.toLowerCase().includes('code') || sourceName.toLowerCase().includes('sanhita');

  const getSourceIcon = () => {
    if (isJudgment) return <Scale className="w-4 h-4 text-primary" />;
    if (isStatute) return <Book className="w-4 h-4 text-primary" />;
    return <FileText className="w-4 h-4 text-primary" />;
  };
  
  const getSourceTypeLabel = () => {
    if (isJudgment) return 'Supreme Court Judgment';
    if (isStatute) return 'Statute';
    if (docType === 'constitution') return 'Constitution';
    return docType ? docType.charAt(0).toUpperCase() + docType.slice(1) : 'Legal Authority';
  };
  
  const relevantPassageText = isJudgment ? "Read relevant judgment passage" : (isStatute ? "Read relevant provision" : "Read relevant passage");

  const metadataRows = [];
  
  if (isJudgment) {
    if (source.metadata?.court) metadataRows.push({ label: 'Court', value: source.metadata.court });
    if (source.metadata?.judgment_date) metadataRows.push({ label: 'Judgment date', value: source.metadata.judgment_date });
    if (source.metadata?.bench) metadataRows.push({ label: 'Bench', value: source.metadata.bench });
    if (source.metadata?.citation) metadataRows.push({ label: 'Citation', value: source.metadata.citation });
    if (source.metadata?.case_number) metadataRows.push({ label: 'Case number', value: source.metadata.case_number });
    if (source.metadata?.petitioner) metadataRows.push({ label: 'Petitioner', value: source.metadata.petitioner });
    if (source.metadata?.respondent) metadataRows.push({ label: 'Respondent', value: source.metadata.respondent });
    if (source.metadata?.case_id) metadataRows.push({ label: 'Case ID', value: source.metadata.case_id });
  } else if (isStatute) {
    metadataRows.push({ label: 'Act/Code', value: sourceName });
    if (source.article_or_section && source.article_or_section !== 'Unknown') metadataRows.push({ label: 'Section/Article', value: source.article_or_section });
    if (source.metadata?.chapter) metadataRows.push({ label: 'Chapter', value: source.metadata.chapter });
    if (source.metadata?.jurisdiction) metadataRows.push({ label: 'Jurisdiction', value: source.metadata.jurisdiction });
  } else {
    if (source.metadata?.authority) metadataRows.push({ label: 'Authority', value: source.metadata.authority });
  }

  // Common metadata
  metadataRows.push({ label: 'Source type', value: getSourceTypeLabel() });
  
  // The full retrieved text
  const fullText = source.full_relevant_text || source.text_snippet || "Text not available.";
  
  return (
    <div className="border border-border rounded-xl bg-surface mb-3 overflow-hidden transition-all duration-200">
      <div 
        className="p-4 cursor-pointer hover:bg-secondary/30 transition-colors flex items-start gap-3"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="mt-0.5 shrink-0">
          <span className="font-semibold text-primary">{source.marker}</span>
        </div>
        
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-text-primary mb-1 pr-6 leading-tight">
            {sourceName}
          </h4>
          
          <div className="text-xs text-text-secondary mb-2">
            {isJudgment && source.metadata?.court && source.metadata.court}
            {isJudgment && !source.metadata?.court && "Supreme Court of India"}
            {isStatute && source.article_or_section !== 'Unknown' && `${source.article_or_section}`}
          </div>
          
          <div className="flex items-center text-xs font-medium text-primary mt-2">
            {isExpanded ? <ChevronDown className="w-4 h-4 mr-1" /> : <ChevronRight className="w-4 h-4 mr-1" />}
            {relevantPassageText}
          </div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="px-4 pb-4 pt-1 border-t border-border bg-background/50">
          <div className="my-4 p-4 bg-surface rounded-lg border border-border/50 text-sm text-text-primary whitespace-pre-wrap leading-relaxed shadow-inner">
            <div className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-2">
              {getSourceIcon()}
              Complete Retrieved Passage
            </div>
            {fullText}
          </div>
          
          <div className="mt-4 pt-4 border-t border-border/50">
            <h5 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">Source Metadata</h5>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
              {metadataRows.map((row, idx) => (
                <div key={idx} className="flex flex-col sm:flex-row sm:items-start text-xs">
                  <span className="text-text-secondary sm:w-32 shrink-0">{row.label}:</span>
                  <span className="text-text-primary font-medium">{row.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExpandableSource;
