# Update Archive Results UI to Tab-based Format

## Problem

ArchiveResultsModal uses old CollapsibleCard format (accordion-style), but should display results using the same tab-based UI as StepByStep processing view (without the execution control panel on the left).

**Current (old):** CollapsibleCards stacked vertically
**Expected (new):** Tab bar + content area (like StepByStep right panel)

## Solution

Rewrite ArchiveResultsModal to use tab-based navigation with specialized result components.

### Changes to ArchiveResultsModal

**File:** [ArchiveResultsModal.tsx](frontend/src/components/archive/ArchiveResultsModal.tsx)

1. **Remove** CollapsibleCard-based layout and `formatObjectAsText()` helper
2. **Add** tab system (same as StepByStep):
   - Tab types: `metadata`, `rawTranscript`, `cleanedTranscript`, `longread`, `summary`, `story`, `chunks`
   - Tab bar with icons (FileText, Zap, BookOpen, etc.)
   - Dynamic tabs based on available data
3. **Use** specialized result components instead of generic text formatting:
   - MetadataView
   - RawTranscriptView, CleanedTranscriptView
   - LongreadView (instead of formatObjectAsText)
   - SummaryView (instead of formatObjectAsText)
   - StoryView
   - ChunksView

### Components to reuse from StepByStep

| Component | Location | Purpose |
|-----------|----------|---------|
| MetadataView | results/MetadataView.tsx | Video metadata display |
| RawTranscriptView | results/TranscriptView.tsx | Raw transcript with metrics |
| CleanedTranscriptView | results/TranscriptView.tsx | Cleaned text with diff button |
| LongreadView | results/LongreadView.tsx | Structured longread display |
| SummaryView | results/SummaryView.tsx | Summary with sections |
| StoryView | results/StoryView.tsx | 8-block leadership story |
| ChunksView | results/ChunksView.tsx | Collapsible chunks list |

### Tab rendering logic (from StepByStep)

```typescript
type ResultTab = 'metadata' | 'rawTranscript' | 'cleanedTranscript' |
                 'longread' | 'summary' | 'story' | 'chunks';

const TAB_CONFIG = {
  metadata: { label: 'Метаданные', icon: FileText },
  rawTranscript: { label: 'Транскрипт', icon: FileText },
  cleanedTranscript: { label: 'Очистка', icon: Zap },
  longread: { label: 'Лонгрид', icon: BookOpen },
  summary: { label: 'Конспект', icon: FileText },
  story: { label: 'История', icon: Users },
  chunks: { label: 'Чанки', icon: Layers },
};

// Get available tabs based on data
function getAvailableTabs(results: PipelineResults): ResultTab[] {
  const tabs: ResultTab[] = [];
  if (results.metadata) tabs.push('metadata');
  if (results.raw_transcript) tabs.push('rawTranscript');
  if (results.cleaned_transcript) tabs.push('cleanedTranscript');
  if (results.longread) tabs.push('longread');
  if (results.summary) tabs.push('summary');
  if (results.story) tabs.push('story');
  if (results.chunks) tabs.push('chunks');
  return tabs;
}
```

### New modal layout

```
┌─────────────────────────────────────────────────┐
│ Title: "SV Тестовая запись"               [X]   │
├─────────────────────────────────────────────────┤
│ [Метаданные] [Транскрипт] [Очистка] [Лонгрид]...│  ← Tab bar
├─────────────────────────────────────────────────┤
│                                                 │
│   Content area - renders selected tab           │
│   Uses specialized components (MetadataView,    │
│   LongreadView, SummaryView, etc.)              │
│                                                 │
├─────────────────────────────────────────────────┤
│                               [Закрыть]         │
└─────────────────────────────────────────────────┘
```

## Files to modify

| File | Changes |
|------|---------|
| [ArchiveResultsModal.tsx](frontend/src/components/archive/ArchiveResultsModal.tsx) | Complete rewrite: tabs + specialized components |

## Verification

1. Deploy: `./scripts/deploy.sh`
2. Open http://100.64.0.1:8802
3. Navigate to Archive → click on record
4. Verify tab-based UI appears (not accordion)
5. Switch between tabs - each shows correct content
6. Check Longread/Summary use proper formatting (sections, not raw text)
