import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface PhaseWrapperProps {
  title?: string;
  description?: string;
  requiresApproval?: boolean;
  status: 'pending' | 'running' | 'gate' | 'complete';
  children: React.ReactNode;
  onApprove?: () => void;
  onRequestRevision?: () => void;
}

export function PhaseWrapper({
  title = 'Phase Output',
  description,
  requiresApproval,
  status,
  children,
  onApprove,
  onRequestRevision,
}: PhaseWrapperProps) {
  return (
    <div className="flex flex-col gap-6 w-full max-w-4xl">
      {/* Streaming output or content */}
      <div className="text-gray-700 leading-relaxed font-mono whitespace-pre-wrap text-sm">
        {children}
      </div>

      {/* Human Gate Review Card */}
      {requiresApproval && status === 'gate' && (
        <Card className="border-orange-200 bg-orange-50/30 shadow-sm mt-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-orange-800 flex items-center gap-2 text-lg">
              <span className="font-bold border border-orange-200 bg-orange-100 text-orange-700 px-2 py-0.5 rounded text-xs select-none">
                HUMAN GATE
              </span>
              {' '}Review {title}
            </CardTitle>
            <CardDescription className="text-orange-700/80">
              {description || 'Requires user approval to proceed to the next phase.'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* The summary or content could go here, or it could be just the buttons. We'll leave it empty for now or put a dummy progress bar. */}
            <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
              <div className="bg-gray-500 h-2 rounded-full w-1/3"></div>
            </div>
          </CardContent>
          <CardFooter className="flex gap-3 justify-end pt-2">
            <Button
              variant="outline"
              className="border-gray-300 text-gray-700 hover:bg-gray-100 bg-white"
              onClick={onRequestRevision}
            >
              Request Revision
            </Button>
            <Button
              className="bg-gray-900 text-white hover:bg-gray-800"
              onClick={onApprove}
            >
              Approve & Continue
            </Button>
          </CardFooter>
        </Card>
      )}
    </div>
  );
}
