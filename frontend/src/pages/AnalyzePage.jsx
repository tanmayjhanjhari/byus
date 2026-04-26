import { useState } from "react";
import PageWrapper from "../components/Layout/PageWrapper";
import ColumnSelector from "../components/Upload/ColumnSelector";
import UploadZone from "../components/Upload/UploadZone";
import PreprocessingReport from "../components/Upload/PreprocessingReport";
import useAnalysisStore from "../store/analysisStore";

export default function AnalyzePage() {
  const sessionId = useAnalysisStore((s) => s.sessionId);
  const preprocessingReport = useAnalysisStore((s) => s.preprocessingReport);

  return (
    <PageWrapper>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-textPrimary mb-1">Upload &amp; Configure</h1>
        <p className="text-textSecondary text-sm">
          Upload your dataset, then select the target variable and sensitive attributes to analyse.
        </p>
      </div>

      {/* Step 1: Upload */}
      <UploadZone />

      {/* Preprocessing Report */}
      {sessionId && preprocessingReport && (
        <div className="mt-6">
          <PreprocessingReport report={preprocessingReport} />
        </div>
      )}

      {/* Step 2: Column selector — visible only after a successful upload */}
      {sessionId && (
        <div className="mt-8">
          <ColumnSelector />
        </div>
      )}
    </PageWrapper>
  );
}
