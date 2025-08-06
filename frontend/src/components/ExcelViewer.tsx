import React, { useState, useEffect } from 'react';
import { HotTable } from '@handsontable/react';
import { registerAllModules } from 'handsontable/registry';
import 'handsontable/dist/handsontable.full.min.css';
import './ExcelViewer.css';

// Register Handsontable modules
registerAllModules();

interface ExcelViewerProps {
  content: string;
  path: string;
  onContentChange?: (content: string) => void;
  readOnly?: boolean;
}

interface ExcelData {
  type: 'excel' | 'csv';
  sheets?: { [key: string]: SheetData };
  sheet_names?: string[];
  columns?: string[];
  data?: any[][];
}

interface SheetData {
  columns: string[];
  data: any[][];
}

const ExcelViewer: React.FC<ExcelViewerProps> = ({ content, path, onContentChange, readOnly = false }) => {
  const [excelData, setExcelData] = useState<ExcelData | null>(null);
  const [activeSheet, setActiveSheet] = useState<string>('');
  const [currentData, setCurrentData] = useState<any[][]>([]);
  const [currentColumns, setCurrentColumns] = useState<string[]>([]);

  useEffect(() => {
    try {
      const parsed = JSON.parse(content) as ExcelData;
      setExcelData(parsed);
      
      if (parsed.type === 'excel' && parsed.sheets && parsed.sheet_names) {
        // Excel file with multiple sheets
        const firstSheet = parsed.sheet_names[0];
        setActiveSheet(firstSheet);
        const sheetData = parsed.sheets[firstSheet];
        if (sheetData) {
          setCurrentColumns(sheetData.columns);
          setCurrentData(sheetData.data);
        }
      } else if (parsed.type === 'csv') {
        // CSV file
        setCurrentColumns(parsed.columns || []);
        setCurrentData(parsed.data || []);
      }
    } catch (error) {
      console.error('Error parsing Excel/CSV data:', error);
    }
  }, [content]);

  const handleSheetChange = (sheetName: string) => {
    if (excelData?.type === 'excel' && excelData.sheets) {
      setActiveSheet(sheetName);
      const sheetData = excelData.sheets[sheetName];
      if (sheetData) {
        setCurrentColumns(sheetData.columns);
        setCurrentData(sheetData.data);
      }
    }
  };

  const handleCellChange = (changes: any[] | null, source: any) => {
    if (!readOnly && changes && onContentChange) {
      // Update the data
      const newData = [...currentData];
      changes.forEach((change) => {
        const [row, col, , newValue] = change;
        if (newData[row] && col !== undefined) {
          newData[row][col] = newValue;
        }
      });
      setCurrentData(newData);
      
      // Update the excelData and notify parent
      if (excelData) {
        const updatedData = { ...excelData };
        if (updatedData.type === 'excel' && updatedData.sheets) {
          updatedData.sheets[activeSheet] = {
            columns: currentColumns,
            data: newData
          };
        } else if (updatedData.type === 'csv') {
          updatedData.data = newData;
        }
        onContentChange(JSON.stringify(updatedData));
      }
    }
  };

  if (!excelData) {
    return <div className="excel-viewer-loading">Loading spreadsheet...</div>;
  }

  const fileName = path.split('/').pop() || '';

  return (
    <div className="excel-viewer">
      <div className="excel-viewer-header">
        <div className="excel-info">
          <span className="excel-filename">{fileName}</span>
          {excelData.type === 'excel' && excelData.sheet_names && (
            <div className="sheet-tabs">
              {excelData.sheet_names.map((sheetName) => (
                <button
                  key={sheetName}
                  className={`sheet-tab ${activeSheet === sheetName ? 'active' : ''}`}
                  onClick={() => handleSheetChange(sheetName)}
                >
                  {sheetName}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="excel-stats">
          <span>{currentData.length} rows</span>
          <span>{currentColumns.length} columns</span>
          {readOnly && <span className="read-only-badge">Read Only</span>}
        </div>
      </div>
      
      <div className="excel-table-container">
        <HotTable
          data={currentData}
          colHeaders={currentColumns}
          rowHeaders={true}
          width="100%"
          height="100%"
          licenseKey="non-commercial-and-evaluation"
          readOnly={readOnly}
          afterChange={handleCellChange}
          settings={{
            stretchH: 'all',
            autoWrapRow: true,
            autoWrapCol: true,
            manualColumnResize: true,
            manualRowResize: true,
            columnSorting: true,
            filters: true,
            dropdownMenu: true,
            contextMenu: true,
            colWidths: 100,
            wordWrap: true
          }}
        />
      </div>
    </div>
  );
};

export default ExcelViewer;