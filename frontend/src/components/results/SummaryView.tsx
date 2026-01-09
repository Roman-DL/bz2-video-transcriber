import type { VideoSummary } from '@/api/types';
import { Card, CardContent, CardHeader } from '@/components/common/Card';
import { Badge } from '@/components/common/Badge';
import {
  FileText,
  Target,
  Lightbulb,
  HelpCircle,
  Tag,
  Users,
  FolderTree,
} from 'lucide-react';

interface SummaryViewProps {
  summary: VideoSummary;
}

export function SummaryView({ summary }: SummaryViewProps) {
  return (
    <div className="space-y-4">
      {/* Main Summary */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-500" />
            <h3 className="text-sm font-medium text-gray-900">Саммари</h3>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {summary.summary}
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        {/* Key Points */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Target className="w-4 h-4 text-gray-500" />
              <h3 className="text-sm font-medium text-gray-900">
                Ключевые тезисы
              </h3>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-gray-700 space-y-2">
              {summary.key_points.map((point, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-blue-500 flex-shrink-0">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        {/* Recommendations */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Lightbulb className="w-4 h-4 text-gray-500" />
              <h3 className="text-sm font-medium text-gray-900">
                Рекомендации
              </h3>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-gray-700 space-y-2">
              {summary.recommendations.map((rec, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-green-500 flex-shrink-0">→</span>
                  <span>{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Questions Answered */}
      {summary.questions_answered.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-gray-500" />
              <h3 className="text-sm font-medium text-gray-900">
                Отвечает на вопросы
              </h3>
            </div>
          </CardHeader>
          <CardContent>
            <ul className="text-sm text-gray-700 space-y-1">
              {summary.questions_answered.map((q, i) => (
                <li key={i}>• {q}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <Card>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-gray-400" />
              <span className="text-gray-500">Аудитория:</span>
              <span className="text-gray-900">{summary.target_audience}</span>
            </div>

            <div className="flex items-center gap-2">
              <FolderTree className="w-4 h-4 text-gray-400" />
              <span className="text-gray-500">Раздел:</span>
              <span className="text-gray-900">
                {summary.section} / {summary.subsection}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Tag className="w-4 h-4 text-gray-400" />
              <div className="flex flex-wrap gap-1">
                {summary.tags.map((tag) => (
                  <Badge key={tag} variant="default">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
