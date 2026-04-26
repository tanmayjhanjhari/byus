import { useState } from "react";
import PageWrapper from "../components/Layout/PageWrapper";
import ColumnSelector from "../components/Upload/ColumnSelector";
import UploadZone from "../components/Upload/UploadZone";
import useAnalysisStore from "../store/analysisStore";

export default function AnalyzePage() {
  const sessionId = useAnalysisStore((s) => s.sessionId);

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

      {/* Step 2: Column selector — visible only after a successful upload */}
      {sessionId && (
        <div className="mt-8">
          <ColumnSelector />
        </div>
      )}
    </PageWrapper>
  );
}
