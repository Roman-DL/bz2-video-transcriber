import { useState } from 'react';
import type { Longread } from '@/api/types';
import { Badge } from '@/components/common/Badge';
import { ChevronDown, ChevronRight } from 'lucide-react';

interface LongreadViewProps {
  longread: Longread;
}

export function LongreadView({ longread }: LongreadViewProps) {
  const [expandedSection, setExpandedSection] = useState<number | null>(null);

  return (
    <div className="space-y-4">
      <div className="text-xs text-gray-500 mb-2">
        Модель: <span className="font-mono">{longread.model_name}</span>
      </div>

      {/* Introduction */}
      {longread.introduction && (
        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-blue-900 mb-2">Вступление</h4>
          <p className="text-sm text-blue-800 whitespace-pre-wrap">
            {longread.introduction}
          </p>
        </div>
      )}

      {/* Sections */}
      <div className="divide-y divide-gray-100">
        {longread.sections.map((section) => (
          <div key={section.index} className="py-3">
            <button
              className="w-full flex items-start gap-2 text-left"
              onClick={() =>
                setExpandedSection(expandedSection === section.index ? null : section.index)
              }
            >
              {expandedSection === section.index ? (
                <ChevronDown className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Badge variant="info">#{section.index}</Badge>
                  <span className="text-sm font-medium text-gray-900">
                    {section.title}
                  </span>
                  <span className="text-xs text-gray-400 ml-auto flex-shrink-0">
                    {section.word_count} слов
                  </span>
                </div>
              </div>
            </button>
            {expandedSection === section.index && (
              <div className="mt-2 ml-6 text-sm text-gray-600 whitespace-pre-wrap bg-gray-50 rounded-lg p-3 max-h-96 overflow-y-auto">
                {section.content}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Conclusion */}
      {longread.conclusion && (
        <div className="bg-green-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-green-900 mb-2">Заключение</h4>
          <p className="text-sm text-green-800 whitespace-pre-wrap">
            {longread.conclusion}
          </p>
        </div>
      )}

      {/* Metadata footer */}
      <div className="pt-4 border-t border-gray-100">
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <div>
            <span className="text-gray-500">Раздел:</span>{' '}
            <span className="text-gray-900">
              {longread.section}
              {longread.subsection && ` / ${longread.subsection}`}
            </span>
          </div>
          {longread.tags.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Теги:</span>
              <div className="flex flex-wrap gap-1">
                {longread.tags.map((tag) => (
                  <Badge key={tag} variant="default">{tag}</Badge>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
