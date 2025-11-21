import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerProps {
  fileUrl: string;
  onClose: () => void;
}

export function PdfViewer({ fileUrl, onClose }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="relative h-[90vh] w-[90vw] flex flex-col bg-white dark:bg-gray-900 rounded-lg overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setPageNumber(Math.max(1, pageNumber - 1))}
              disabled={pageNumber <= 1}
              className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700 disabled:opacity-50"
            >
              ←
            </button>
            <span className="text-sm">
              {pageNumber} / {numPages}
            </span>
            <button
              onClick={() => setPageNumber(Math.min(numPages, pageNumber + 1))}
              disabled={pageNumber >= numPages}
              className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700 disabled:opacity-50"
            >
              →
            </button>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setScale(Math.max(0.5, scale - 0.1))}
              className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700"
            >
              -
            </button>
            <span className="text-sm">{Math.round(scale * 100)}%</span>
            <button
              onClick={() => setScale(Math.min(2.0, scale + 0.1))}
              className="px-3 py-1 rounded bg-gray-200 dark:bg-gray-700"
            >
              +
            </button>
          </div>

          <button
            onClick={onClose}
            className="px-4 py-2 rounded bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
          >
            닫기
          </button>
        </div>

        {/* PDF Content */}
        <div className="flex-1 overflow-auto flex items-center justify-center p-4 bg-gray-100 dark:bg-gray-800">
          <Document file={fileUrl} onLoadSuccess={onDocumentLoadSuccess}>
            <Page pageNumber={pageNumber} scale={scale} />
          </Document>
        </div>
      </div>
    </div>
  );
}
