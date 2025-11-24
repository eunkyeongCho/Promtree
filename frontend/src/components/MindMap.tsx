import { useEffect, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

interface Node {
  id: string;
  name: string;
  type: string;
  val?: number;
}

interface Link {
  source: string;
  target: string;
  label: string;
}

interface GraphData {
  nodes: Node[];
  links: Link[];
}

export function MindMap() {
  const graphRef = useRef<any>();
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });

  useEffect(() => {
    // 샘플 데이터 - 나중에 API로 교체
    const sampleData: GraphData = {
      nodes: [
        { id: '1', name: 'TDS', type: 'document', val: 20 },
        { id: '2', name: 'Tg', type: 'property', val: 15 },
        { id: '3', name: 'Polymer X', type: 'material', val: 18 },
        { id: '4', name: '85°C', type: 'value', val: 10 },
        { id: '5', name: 'Tm', type: 'property', val: 15 },
        { id: '6', name: '160°C', type: 'value', val: 10 },
        { id: '7', name: 'MSDS', type: 'document', val: 20 },
        { id: '8', name: 'Safety', type: 'category', val: 12 },
      ],
      links: [
        { source: '1', target: '3', label: 'describes' },
        { source: '3', target: '2', label: 'has_property' },
        { source: '2', target: '4', label: 'value' },
        { source: '3', target: '5', label: 'has_property' },
        { source: '5', target: '6', label: 'value' },
        { source: '7', target: '3', label: 'describes' },
        { source: '7', target: '8', label: 'contains' },
      ],
    };
    setGraphData(sampleData);
  }, []);

  const getNodeColor = (node: Node) => {
    switch (node.type) {
      case 'document': return '#3b82f6';
      case 'material': return '#10b981';
      case 'property': return '#f59e0b';
      case 'value': return '#ef4444';
      case 'category': return '#8b5cf6';
      default: return '#6b7280';
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="flex h-16 items-center border-b border-border px-6">
        <h1 className="text-2xl font-bold text-foreground">Knowledge Graph</h1>
      </header>
      <div className="flex-1 relative">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData}
          nodeLabel="name"
          nodeColor={getNodeColor}
          nodeRelSize={6}
          linkLabel="label"
          linkDirectionalArrowLength={3.5}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.25}
          enableNodeDrag={true}
          enableZoomPanInteraction={true}
          backgroundColor="transparent"
        />
      </div>
    </div>
  );
}
