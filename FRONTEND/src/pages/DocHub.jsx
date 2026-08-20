import React, { useState } from 'react';

import PageContainer from '../components/common/PageContainer';

import Card from '../components/common/Card';

import Button from '../components/common/Button';

import LoadingSpinner from '../components/common/LoadingSpinner';

import { Link } from 'react-router-dom';

import { generateDraft, editDraft, downloadPdf, downloadDocx } from '../services/draftingService';

import Toast from '../components/common/Toast';

import { useAuth } from '../contexts/AuthContext';



export default function DocHub() {

  const { currentUser } = useAuth();

  const [step, setStep] = useState(1);

  const [userFacts, setUserFacts] = useState("");

  const [isGenerating, setIsGenerating] = useState(false);

  const [error, setError] = useState("");

  const [toastMessage, setToastMessage] = useState("");

  const [isToastOpen, setIsToastOpen] = useState(false);



  // Edit States

  const [isEditing, setIsEditing] = useState(false);

  const [editInstructions, setEditInstructions] = useState("");



  // Draft Result States

  const [draftResult, setDraftResult] = useState(null);

  const [missingInfo, setMissingInfo] = useState({ documentType: "", fields: [], provided: {} });



  const handleGenerate = async (providedFields = null) => {

    if (!userFacts.trim()) {

      setError("Please describe the situation first.");

      return;

    }

    setError("");

    setIsGenerating(true);

    setStep(2); // Generating/Analyzing step

    

    try {

      const token = await currentUser?.getIdToken(true);
      if (!token) throw new Error('Please sign in to generate a draft.');
      const result = await generateDraft(token, userFacts, providedFields);

      

      if (result.status === "MISSING_INFO") {

        setMissingInfo({

          documentType: result.document_type,

          fields: result.missing_fields,

          provided: providedFields || {}

        });

        setStep(3); // Missing Info Wizard

      } else if (result.status === "SUCCESS") {

        setDraftResult(result.document_object);

        setStep(4); // Professional Preview

      } else if (result.status === "ERROR") {

        setError(result.message || "An error occurred while generating the draft.");

        setStep(1);

      } else {

        setError("Unexpected response from server.");

        setStep(1);

      }

    } catch (err) {

      console.error(err);

      setError("Failed to generate draft. Please try again.");

      setStep(1);

    } finally {

      setIsGenerating(false);

    }

  };



  const handleEditSubmit = async () => {

    if (!editInstructions.trim()) return;

    setError("");

    setIsGenerating(true);

    try {

      const token = await currentUser?.getIdToken(true);
      const result = await editDraft(token, draftResult, editInstructions);

      setDraftResult(result);

      setEditInstructions("");

      setIsEditing(false);

      setToastMessage(`Updated to V${result.metadata.version}`);

      setIsToastOpen(true);

    } catch (err) {

      console.error(err);

      setError("Failed to edit draft.");

    } finally {

      setIsGenerating(false);

    }

  };



  const handleMissingInfoSubmit = () => {

    handleGenerate(missingInfo.provided);

  };



  const handleDownloadPdf = async () => {

    try {

      setToastMessage("Generating PDF...");

      setIsToastOpen(true);

      const token = await currentUser?.getIdToken(true);
      const blob = await downloadPdf(token, draftResult);

      const url = window.URL.createObjectURL(blob);

      const a = document.createElement('a');

      a.href = url;

      a.download = `${draftResult.document_type.toLowerCase()}_v${draftResult.metadata.version}.pdf`;

      document.body.appendChild(a);

      a.click();

      a.remove();

      window.URL.revokeObjectURL(url);

    } catch (err) {

      setError("Failed to generate PDF.");

    }

  };



  const handleDownloadDocx = async () => {

    try {

      setToastMessage("Generating DOCX...");

      setIsToastOpen(true);

      const token = await currentUser?.getIdToken(true);
      const blob = await downloadDocx(token, draftResult);

      const url = window.URL.createObjectURL(blob);

      const a = document.createElement('a');

      a.href = url;

      a.download = `${draftResult.document_type.toLowerCase()}_v${draftResult.metadata.version}.docx`;

      document.body.appendChild(a);

      a.click();

      a.remove();

      window.URL.revokeObjectURL(url);

    } catch (err) {

      setError("Failed to generate DOCX.");

    }

  };



  const handleCopyText = () => {

    if (!draftResult) return;

    const text = draftResult.body.join("\n\n");

    navigator.clipboard.writeText(text);

    setToastMessage("Draft text copied to clipboard!");

    setIsToastOpen(true);

  };



  const renderA4Document = () => {

    if (!draftResult) return null;

    return (

      <div className="w-[210mm] min-h-[297mm] bg-white text-black p-[25.4mm] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1),0_0_0_1px_rgba(0,0,0,0.05)] mx-auto font-serif text-[12pt] leading-normal mb-10 relative">

        {/* Subtle page texture/grain could go here, but keeping it clean for now */}

        {draftResult.title && (

          <h1 className="text-center font-bold text-[14pt] mb-8 uppercase underline underline-offset-4">{draftResult.title}</h1>

        )}

        

        <div className="mb-6 space-y-2">

          {Object.entries(draftResult.parties).map(([key, value], idx) => (

            <div key={idx} className="flex">

              <span className="font-bold mr-2 capitalize">{key.replace('_', ' ')}:</span>

              <span>{value}</span>

            </div>

          ))}

        </div>

        

        <div className="space-y-4 text-justify">

          {draftResult.body.map((para, idx) => (

            <p key={idx} className="indent-8">{para}</p>

          ))}

        </div>

        

        {draftResult.verification && draftResult.verification.text && (

          <div className="mt-10">

            <h2 className="text-center font-bold text-[14pt] mb-4">VERIFICATION</h2>

            <p className="text-justify mb-4">{draftResult.verification.text}</p>

            <div className="flex flex-col gap-2">

              <p>Date: {draftResult.verification.date}</p>

              <p>Place: {draftResult.verification.place}</p>

            </div>

          </div>

        )}

        

        {draftResult.signature_blocks && draftResult.signature_blocks.length > 0 && (

          <div className="mt-16 flex flex-col items-end gap-12">

            {draftResult.signature_blocks.map((sig, idx) => (

              <div key={idx} className="text-center min-w-[200px]">

                <div className="border-b border-black mb-2 w-full"></div>

                <p className="font-bold">{sig}</p>

              </div>

            ))}

          </div>

        )}

        

        {draftResult.annexures && draftResult.annexures.length > 0 && (

          <div className="mt-16 break-before-page">

            <h2 className="text-center font-bold text-[14pt] mb-4">ANNEXURES</h2>

            <ol className="list-decimal list-inside space-y-2">

              {draftResult.annexures.map((ann, idx) => (

                <li key={idx}>{ann}</li>

              ))}

            </ol>

          </div>

        )}

      </div>

    );

  };



  return (

    <PageContainer>

      <div className="flex flex-col gap-6 text-left max-w-5xl mx-auto mt-4 pb-20">

        {/* Breadcrumb */}

        <Link to="/dashboard" className="flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-text-secondary hover:text-primary transition-colors">

          <span className="material-symbols-outlined text-[16px]">arrow_back</span>

          Dashboard

        </Link>



        {/* Header */}

        <div>

          <span className="text-[10px] font-bold text-text-primary uppercase tracking-widest bg-secondary px-3 py-1.5 rounded-button border border-border">

            NYAAY AI Engine

          </span>

          <h1 className="text-3xl font-semibold tracking-tighter mt-4 text-primary">Document Drafting</h1>

          <p className="text-sm text-text-secondary mt-1">

            Generate production-grade, filing-ready legal documents.

          </p>

        </div>



        {error && (

          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">

            {error}

          </div>

        )}



        {/* Step 1: Input Facts */}

        {step === 1 && (

          <Card className="p-8">

            <h2 className="text-xl font-bold mb-4">Describe the Situation</h2>

            <p className="text-sm text-text-secondary mb-4">

              Explain your issue in plain language. The AI will determine the correct document type and format it appropriately.

            </p>

            <textarea

              className="w-full h-48 p-4 border border-border bg-background rounded-input focus:outline-none focus:ring-4 focus:ring-primary/10 focus:border-border-hover resize-none text-sm text-primary placeholder:text-text-muted transition-all duration-200"

              placeholder="E.g., I bought a washing machine from SuperStore on 12th Jan 2024 for 25000 INR. It stopped working after a week. They are refusing to replace it or refund my money..."

              value={userFacts}

              onChange={(e) => setUserFacts(e.target.value)}

            />

            <div className="mt-4 flex justify-end">

              <Button onClick={() => handleGenerate(null)} disabled={!userFacts.trim() || isGenerating}>

                Analyze & Draft

              </Button>

            </div>

          </Card>

        )}



        {/* Step 2: Generating / Analyzing */}

        {(step === 2 || (step === 4 && isGenerating)) && (

          <Card className="p-16 flex flex-col items-center justify-center">

            <LoadingSpinner size="lg" color="indigo" />

            <h2 className="text-xl font-bold mt-6">{step === 4 ? "Applying Edits..." : "Analyzing Facts..."}</h2>

            <p className="text-sm text-text-secondary mt-2 text-center max-w-md">

              {step === 4 ? "Re-drafting the document based on your instructions." : "Identifying the correct document type and retrieving legal formats."}

            </p>

          </Card>

        )}



        {/* Step 3: Missing Info Wizard */}

        {step === 3 && (

          <Card className="p-8">

            <h2 className="text-xl font-bold mb-2 text-primary">Missing Information Required</h2>

            <p className="text-sm text-primary mb-6 bg-secondary p-4 rounded-xl border border-border">

              We've identified that you need a <strong>{missingInfo.documentType.replace(/_/g, ' ')}</strong>. To draft a legally sound document, please provide the following essential details.

            </p>

            

            <div className="space-y-4">

              {missingInfo.fields.map(field => (

                <div key={field} className="flex flex-col gap-1">

                  <label className="text-sm font-semibold capitalize">{field.replace(/_/g, ' ')}</label>

                  <input

                    type="text"

                    className="p-3 bg-background border border-border rounded-input focus:ring-4 focus:ring-primary/10 focus:border-border-hover focus:outline-none text-sm w-full max-w-md transition-all duration-200"

                    placeholder={`Enter ${field.replace(/_/g, ' ')}`}

                    value={missingInfo.provided[field] || ""}

                    onChange={(e) => setMissingInfo(prev => ({

                      ...prev,

                      provided: { ...prev.provided, [field]: e.target.value }

                    }))}

                  />

                </div>

              ))}

            </div>

            

            <div className="mt-8 flex justify-end gap-3">

              <Button variant="outline" onClick={() => setStep(1)}>Back</Button>

              <Button onClick={handleMissingInfoSubmit}>Generate Final Draft</Button>

            </div>

          </Card>

        )}



        {/* Step 4: Final Preview */}

        {step === 4 && !isGenerating && draftResult && (

          <div className="flex flex-col gap-6">

            {/* Professional Toolbar */}

            <div className="sticky top-4 z-20 bg-surface/80 backdrop-blur-xl p-4 border border-border rounded-2xl shadow-toolbar flex flex-col gap-3">

              <div className="flex flex-wrap items-center justify-between">

                <div className="font-semibold text-sm px-2 text-primary tracking-tight">

                  Draft V{draftResult.metadata.version} • {draftResult.document_type.replace(/_/g, ' ')}

                </div>

                <div className="flex gap-2">

                  <Button variant="outline" onClick={() => window.print()} className="!py-2 !px-3 text-xs flex items-center gap-1 shadow-sm">

                    <span className="material-symbols-outlined text-[16px]">print</span> Print

                  </Button>

                  <Button variant="outline" onClick={handleDownloadPdf} className="!py-2 !px-3 text-xs flex items-center gap-1 shadow-sm hover:text-error hover:border-error/30">

                    <span className="material-symbols-outlined text-[16px]">picture_as_pdf</span> PDF

                  </Button>

                  <Button variant="outline" onClick={handleDownloadDocx} className="!py-2 !px-3 text-xs flex items-center gap-1 shadow-sm hover:text-blue-600 hover:border-blue-600/30">

                    <span className="material-symbols-outlined text-[16px]">description</span> DOCX

                  </Button>

                  <div className="w-px h-6 bg-border mx-1 self-center"></div>

                  <Button variant="outline" onClick={() => setIsEditing(!isEditing)} className={`!py-2 !px-3 text-xs shadow-sm ${isEditing ? 'bg-secondary text-primary border-border-hover' : ''}`}>

                    <span className="material-symbols-outlined text-[16px] mr-1 align-middle">edit</span>

                    Edit Draft

                  </Button>

                  <Button variant="outline" onClick={handleCopyText} className="!py-2 !px-3 text-xs shadow-sm">Copy Text</Button>

                  <Button variant="outline" onClick={() => setStep(1)} className="!py-2 !px-3 text-xs shadow-sm">Start Over</Button>

                </div>

              </div>



              {/* Edit Panel */}

              {isEditing && (

                <div className="pt-3 border-t border-zinc-200 flex gap-2">

                  <input 

                    type="text" 

                    className="flex-1 p-3 bg-background border border-border rounded-input text-sm focus:outline-none focus:ring-4 focus:ring-primary/10 focus:border-border-hover transition-all" 

                    placeholder="E.g., Make the 3rd paragraph more aggressive, or add my middle name 'Kumar'..."

                    value={editInstructions}

                    onChange={(e) => setEditInstructions(e.target.value)}

                    onKeyDown={(e) => e.key === 'Enter' && handleEditSubmit()}

                  />

                  <Button onClick={handleEditSubmit} disabled={!editInstructions.trim()} className="!py-2 !px-4 text-xs">

                    Apply Edit

                  </Button>

                </div>

              )}

            </div>



            {/* A4 Document Preview */}

            <div className="overflow-x-auto bg-[#E5E5E5] p-12 rounded-3xl shadow-inner flex justify-center border border-border/50">

              {renderA4Document()}

            </div>

          </div>

        )}

      </div>

      

      <Toast

        message={toastMessage}

        isOpen={isToastOpen}

        onClose={() => setIsToastOpen(false)}

      />

    </PageContainer>

  );

}

