/**
 * DentalVision Pro — Odontogram React Component
 * File: dental_vision/public/js/odontogram/Odontogram.jsx
 *
 * Interactive SVG tooth chart with:
 *  - Click-to-select teeth
 *  - Surface-level condition painting (5 zones per tooth)
 *  - Condition palette (Caries, Crown, Missing, Filling variants, etc.)
 *  - Auto-save to Frappe backend via REST API
 *  - Undo stack (last 10 states)
 */

import React, { useState, useEffect, useCallback, useRef } from "react";

// ─────────────────────────────────────────────
// Constants & Configuration
// ─────────────────────────────────────────────

const CONDITION_COLORS = {
  "Healthy":               "#22c55e",
  "Caries":                "#ef4444",
  "Filling - Composite":   "#3b82f6",
  "Filling - Amalgam":     "#374151",
  "Filling - Gold":        "#f59e0b",
  "Filling - Ceramic":     "#e0e7ff",
  "Crown":                 "#f59e0b",
  "Missing":               "#9ca3af",
  "Extracted":             "#6b7280",
  "Implant":               "#8b5cf6",
  "RCT - Root Canal":      "#ec4899",
  "Veneer":                "#a5f3fc",
  "Sealant":               "#bbf7d0",
  "Fracture":              "#dc2626",
  "Watched":               "#fbbf24",
  "Bridge Abutment":       "#f59e0b",
  "Bridge Pontic":         "#d1d5db",
};

const CONDITIONS = Object.keys(CONDITION_COLORS);

// Universal Numbering System layout
// Upper: 1-16 (right to left), Lower: 17-32 (left to right)
const UPPER_TEETH = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16];
const LOWER_TEETH = [32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17];

const TOOTH_NAMES = {
  1: "UR3M", 2: "UR2M", 3: "UR1M", 4: "UR1P", 5: "UR2P",
  6: "URC",  7: "URI2", 8: "URI1", 9: "ULI1", 10: "ULI2",
  11: "ULC", 12: "UL2P", 13: "UL1P", 14: "UL1M", 15: "UL2M", 16: "UL3M",
  17: "LL3M", 18: "LL2M", 19: "LL1M", 20: "LL1P", 21: "LL2P",
  22: "LLC", 23: "LLI2", 24: "LLI1", 25: "LRI1", 26: "LRI2",
  27: "LRC", 28: "LR2P", 29: "LR1P", 30: "LR1M", 31: "LR2M", 32: "LR3M",
};

// ─────────────────────────────────────────────
// Default blank tooth state
// ─────────────────────────────────────────────

function defaultToothState(num) {
  return {
    tooth_number: String(num),
    overall_condition: "Healthy",
    surfaces: { M: "Healthy", D: "Healthy", O: "Healthy", B: "Healthy", L: "Healthy" },
    mobility: "0",
    notes: "",
    is_missing: false,
    is_implant: false,
    is_crown: false,
    is_rct: false,
  };
}

function buildDefaultChart() {
  const chart = {};
  [...UPPER_TEETH, ...LOWER_TEETH].forEach((n) => {
    chart[String(n)] = defaultToothState(n);
  });
  return chart;
}

// ─────────────────────────────────────────────
// SVG Tooth Component
// Each tooth renders as a 5-zone SVG square
// ─────────────────────────────────────────────

function ToothSVG({ toothNum, toothState, isSelected, onClick, onSurfaceClick, isUpper }) {
  const s = toothState;
  const surfaceColor = (key) => CONDITION_COLORS[s.surfaces[key]] || "#22c55e";
  const borderColor = isSelected ? "#2563eb" : "#64748b";
  const borderWidth = isSelected ? 2.5 : 1;

  if (s.is_missing || s.overall_condition === "Missing" || s.overall_condition === "Extracted") {
    return (
      <g onClick={onClick} style={{ cursor: "pointer" }}>
        <rect x={2} y={2} width={44} height={44} rx={4}
          fill="#f1f5f9" stroke={borderColor} strokeWidth={borderWidth} />
        <line x1={6} y1={6} x2={42} y2={42} stroke="#94a3b8" strokeWidth={1.5} />
        <line x1={42} y1={6} x2={6} y2={42} stroke="#94a3b8" strokeWidth={1.5} />
        <text x={24} y={54} textAnchor="middle" fontSize={9} fill="#64748b" fontFamily="monospace">
          {toothNum}
        </text>
      </g>
    );
  }

  // Crown: solid gold overlay
  if (s.overall_condition === "Crown" || s.is_crown) {
    return (
      <g onClick={onClick} style={{ cursor: "pointer" }}>
        <rect x={2} y={2} width={44} height={44} rx={4}
          fill="#f59e0b" stroke={borderColor} strokeWidth={borderWidth} opacity={0.85} />
        <text x={24} y={28} textAnchor="middle" fontSize={10} fill="white" fontWeight="bold" fontFamily="sans-serif">C</text>
        <text x={24} y={54} textAnchor="middle" fontSize={9} fill="#64748b" fontFamily="monospace">{toothNum}</text>
      </g>
    );
  }

  // Implant: purple with I
  if (s.overall_condition === "Implant" || s.is_implant) {
    return (
      <g onClick={onClick} style={{ cursor: "pointer" }}>
        <rect x={2} y={2} width={44} height={44} rx={4}
          fill="#8b5cf6" stroke={borderColor} strokeWidth={borderWidth} opacity={0.85} />
        <text x={24} y={28} textAnchor="middle" fontSize={10} fill="white" fontWeight="bold" fontFamily="sans-serif">IMP</text>
        <text x={24} y={54} textAnchor="middle" fontSize={9} fill="#64748b" fontFamily="monospace">{toothNum}</text>
      </g>
    );
  }

  // RCT: pink dot in center
  const rctOverlay = s.is_rct || s.overall_condition === "RCT - Root Canal" ? (
    <circle cx={24} cy={24} r={6} fill="#ec4899" opacity={0.8} />
  ) : null;

  // Standard 5-surface tooth
  return (
    <g onClick={onClick} style={{ cursor: "pointer" }}>
      {/* Outer border */}
      <rect x={2} y={2} width={44} height={44} rx={4}
        fill="white" stroke={borderColor} strokeWidth={borderWidth} />

      {/* Occlusal center square */}
      <rect x={14} y={14} width={20} height={20}
        fill={surfaceColor("O")} stroke="#cbd5e1" strokeWidth={0.5}
        onClick={(e) => { e.stopPropagation(); onSurfaceClick("O"); }}
        style={{ cursor: "crosshair" }} />

      {/* Mesial (left) */}
      <polygon points="2,2 14,14 14,34 2,46"
        fill={surfaceColor("M")} stroke="#cbd5e1" strokeWidth={0.5}
        onClick={(e) => { e.stopPropagation(); onSurfaceClick("M"); }}
        style={{ cursor: "crosshair" }} />

      {/* Distal (right) */}
      <polygon points="46,2 34,14 34,34 46,46"
        fill={surfaceColor("D")} stroke="#cbd5e1" strokeWidth={0.5}
        onClick={(e) => { e.stopPropagation(); onSurfaceClick("D"); }}
        style={{ cursor: "crosshair" }} />

      {/* Buccal/Facial: top for upper, bottom for lower */}
      {isUpper ? (
        <polygon points="2,2 46,2 34,14 14,14"
          fill={surfaceColor("B")} stroke="#cbd5e1" strokeWidth={0.5}
          onClick={(e) => { e.stopPropagation(); onSurfaceClick("B"); }}
          style={{ cursor: "crosshair" }} />
      ) : (
        <polygon points="2,46 46,46 34,34 14,34"
          fill={surfaceColor("B")} stroke="#cbd5e1" strokeWidth={0.5}
          onClick={(e) => { e.stopPropagation(); onSurfaceClick("B"); }}
          style={{ cursor: "crosshair" }} />
      )}

      {/* Lingual/Palatal: bottom for upper, top for lower */}
      {isUpper ? (
        <polygon points="2,46 46,46 34,34 14,34"
          fill={surfaceColor("L")} stroke="#cbd5e1" strokeWidth={0.5}
          onClick={(e) => { e.stopPropagation(); onSurfaceClick("L"); }}
          style={{ cursor: "crosshair" }} />
      ) : (
        <polygon points="2,2 46,2 34,14 14,14"
          fill={surfaceColor("L")} stroke="#cbd5e1" strokeWidth={0.5}
          onClick={(e) => { e.stopPropagation(); onSurfaceClick("L"); }}
          style={{ cursor: "crosshair" }} />
      )}

      {/* RCT overlay */}
      {rctOverlay}

      {/* Tooth number label */}
      <text x={24} y={54} textAnchor="middle" fontSize={9} fill="#475569" fontFamily="monospace">
        {toothNum}
      </text>
    </g>
  );
}

// ─────────────────────────────────────────────
// Condition Palette
// ─────────────────────────────────────────────

function ConditionPalette({ selectedCondition, onSelect }) {
  return (
    <div style={{
      display: "flex", flexWrap: "wrap", gap: "6px",
      padding: "12px", background: "#f8fafc",
      borderRadius: "8px", border: "1px solid #e2e8f0"
    }}>
      <div style={{ width: "100%", fontSize: "11px", fontWeight: 600,
        color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em",
        marginBottom: "4px" }}>
        Condition Palette
      </div>
      {CONDITIONS.map((cond) => (
        <button
          key={cond}
          onClick={() => onSelect(cond)}
          title={cond}
          style={{
            display: "flex", alignItems: "center", gap: "5px",
            padding: "4px 8px", borderRadius: "4px",
            border: selectedCondition === cond ? "2px solid #2563eb" : "1px solid #cbd5e1",
            background: selectedCondition === cond ? "#eff6ff" : "white",
            cursor: "pointer", fontSize: "11px", color: "#1e293b",
            fontWeight: selectedCondition === cond ? 600 : 400,
          }}
        >
          <span style={{
            width: "12px", height: "12px", borderRadius: "3px",
            background: CONDITION_COLORS[cond],
            border: "1px solid rgba(0,0,0,0.1)",
            flexShrink: 0
          }} />
          {cond}
        </button>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
// Tooth Detail Panel
// ─────────────────────────────────────────────

function ToothDetailPanel({ toothNum, toothState, onUpdateSurface, onUpdateOverall, onUpdateNotes }) {
  if (!toothNum) {
    return (
      <div style={{ padding: "24px", textAlign: "center", color: "#94a3b8" }}>
        <div style={{ fontSize: "32px", marginBottom: "8px" }}>🦷</div>
        <div style={{ fontSize: "13px" }}>Click any tooth to view and edit its details</div>
      </div>
    );
  }

  const s = toothState;
  const surfaces = ["M", "D", "O", "B", "L"];
  const surfaceNames = { M: "Mesial", D: "Distal", O: "Occlusal/Incisal", B: "Buccal/Facial", L: "Lingual/Palatal" };

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ fontWeight: 700, fontSize: "16px", color: "#0f172a", marginBottom: "12px" }}>
        Tooth #{toothNum} — {TOOTH_NAMES[toothNum] || ""}
      </div>

      {/* Overall condition */}
      <div style={{ marginBottom: "12px" }}>
        <label style={{ fontSize: "11px", fontWeight: 600, color: "#64748b",
          textTransform: "uppercase", display: "block", marginBottom: "4px" }}>
          Overall Condition
        </label>
        <select
          value={s.overall_condition}
          onChange={(e) => onUpdateOverall(toothNum, e.target.value)}
          style={{ width: "100%", padding: "6px 8px", borderRadius: "6px",
            border: "1px solid #cbd5e1", fontSize: "13px" }}
        >
          {CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Per-surface conditions */}
      <div style={{ marginBottom: "12px" }}>
        <label style={{ fontSize: "11px", fontWeight: 600, color: "#64748b",
          textTransform: "uppercase", display: "block", marginBottom: "4px" }}>
          Surface Conditions
        </label>
        {surfaces.map((surf) => (
          <div key={surf} style={{ display: "flex", alignItems: "center",
            gap: "8px", marginBottom: "4px" }}>
            <span style={{ width: "120px", fontSize: "12px", color: "#475569" }}>
              {surfaceNames[surf]}
            </span>
            <span style={{ width: "12px", height: "12px", borderRadius: "3px",
              background: CONDITION_COLORS[s.surfaces[surf]] || "#22c55e",
              border: "1px solid rgba(0,0,0,0.1)", flexShrink: 0 }} />
            <select
              value={s.surfaces[surf]}
              onChange={(e) => onUpdateSurface(toothNum, surf, e.target.value)}
              style={{ flex: 1, padding: "3px 6px", borderRadius: "4px",
                border: "1px solid #cbd5e1", fontSize: "12px" }}
            >
              {CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        ))}
      </div>

      {/* Notes */}
      <div>
        <label style={{ fontSize: "11px", fontWeight: 600, color: "#64748b",
          textTransform: "uppercase", display: "block", marginBottom: "4px" }}>
          Clinical Note
        </label>
        <textarea
          value={s.notes}
          onChange={(e) => onUpdateNotes(toothNum, e.target.value)}
          rows={3}
          style={{ width: "100%", padding: "6px 8px", borderRadius: "6px",
            border: "1px solid #cbd5e1", fontSize: "12px", resize: "vertical",
            fontFamily: "inherit" }}
          placeholder="e.g. Sensitivity noted, watch for caries progression..."
        />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// Main Odontogram Component
// ─────────────────────────────────────────────

export default function Odontogram({ patientId, encounterName, readOnly = false }) {
  const [chart, setChart] = useState(buildDefaultChart());
  const [selectedTooth, setSelectedTooth] = useState(null);
  const [selectedCondition, setSelectedCondition] = useState("Caries");
  const [paintMode, setPaintMode] = useState("surface"); // "surface" | "overall"
  const [saveStatus, setSaveStatus] = useState("saved"); // "saved" | "unsaved" | "saving" | "error"
  const [undoStack, setUndoStack] = useState([]);
  const [showLegend, setShowLegend] = useState(false);
  const saveTimer = useRef(null);

  // ── Load chart from backend ──
  useEffect(() => {
    if (!patientId) return;
    frappe.call({
      method: "dental_vision.api.odontogram.get_chart_state",
      args: { patient: patientId, encounter: encounterName || "" },
      callback: (r) => {
        if (r.message && r.message.length > 0) {
          const loaded = {};
          r.message.forEach((t) => { loaded[t.tooth_number] = t; });
          setChart((prev) => ({ ...prev, ...loaded }));
        }
      },
    });
  }, [patientId, encounterName]);

  // ── Auto-save with debounce ──
  useEffect(() => {
    if (saveStatus !== "unsaved" || readOnly) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => saveChart(), 2500);
    return () => clearTimeout(saveTimer.current);
  }, [chart, saveStatus]);

  const pushUndo = useCallback((prevChart) => {
    setUndoStack((stack) => [...stack.slice(-9), prevChart]);
  }, []);

  const undo = useCallback(() => {
    if (undoStack.length === 0) return;
    const prev = undoStack[undoStack.length - 1];
    setChart(prev);
    setUndoStack((stack) => stack.slice(0, -1));
    setSaveStatus("unsaved");
  }, [undoStack]);

  const updateSurface = useCallback((toothNum, surface, condition) => {
    if (readOnly) return;
    setChart((prev) => {
      pushUndo(prev);
      const tooth = { ...prev[String(toothNum)] };
      tooth.surfaces = { ...tooth.surfaces, [surface]: condition };
      return { ...prev, [String(toothNum)]: tooth };
    });
    setSaveStatus("unsaved");
  }, [readOnly, pushUndo]);

  const updateOverall = useCallback((toothNum, condition) => {
    if (readOnly) return;
    setChart((prev) => {
      pushUndo(prev);
      const tooth = { ...prev[String(toothNum)] };
      tooth.overall_condition = condition;
      tooth.is_missing = ["Missing", "Extracted"].includes(condition);
      tooth.is_implant = condition === "Implant";
      tooth.is_crown = condition === "Crown";
      tooth.is_rct = condition === "RCT - Root Canal";
      return { ...prev, [String(toothNum)]: tooth };
    });
    setSaveStatus("unsaved");
  }, [readOnly, pushUndo]);

  const updateNotes = useCallback((toothNum, notes) => {
    if (readOnly) return;
    setChart((prev) => {
      const tooth = { ...prev[String(toothNum)], notes };
      return { ...prev, [String(toothNum)]: tooth };
    });
    setSaveStatus("unsaved");
  }, [readOnly]);

  const handleToothClick = (toothNum) => {
    setSelectedTooth(String(toothNum));
  };

  const handleSurfaceClick = (toothNum, surface) => {
    if (readOnly) return;
    if (paintMode === "surface") {
      updateSurface(toothNum, surface, selectedCondition);
    } else {
      updateOverall(toothNum, selectedCondition);
    }
  };

  const saveChart = async () => {
    if (!encounterName) return;
    setSaveStatus("saving");
    frappe.call({
      method: "dental_vision.api.odontogram.save_chart_state",
      args: {
        encounter: encounterName,
        chart_json: JSON.stringify(chart),
      },
      callback: (r) => {
        if (r.exc) {
          setSaveStatus("error");
          frappe.msgprint({ message: "Failed to save odontogram.", indicator: "red" });
        } else {
          setSaveStatus("saved");
        }
      },
    });
  };

  // ── Render a row of teeth ──
  const renderTeethRow = (teeth, isUpper) => (
    <div style={{ display: "flex", gap: "4px", justifyContent: "center", padding: "8px 0" }}>
      {teeth.map((num) => (
        <svg key={num} width={48} height={60} viewBox="0 0 48 60"
          style={{ overflow: "visible" }}>
          <ToothSVG
            toothNum={num}
            toothState={chart[String(num)] || defaultToothState(num)}
            isSelected={selectedTooth === String(num)}
            isUpper={isUpper}
            onClick={() => handleToothClick(num)}
            onSurfaceClick={(surface) => handleSurfaceClick(num, surface)}
          />
        </svg>
      ))}
    </div>
  );

  const statusColors = { saved: "#22c55e", unsaved: "#f59e0b", saving: "#3b82f6", error: "#ef4444" };
  const statusLabels = { saved: "Saved", unsaved: "Unsaved changes", saving: "Saving...", error: "Save failed" };

  return (
    <div style={{ fontFamily: "'Inter', system-ui, sans-serif", background: "#f8fafc",
      borderRadius: "12px", border: "1px solid #e2e8f0", overflow: "hidden" }}>

      {/* ── Toolbar ── */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 16px", background: "white", borderBottom: "1px solid #e2e8f0" }}>
        <div style={{ fontWeight: 700, fontSize: "15px", color: "#0f172a" }}>
          🦷 Odontogram
          {patientId && <span style={{ fontWeight: 400, color: "#64748b", marginLeft: "8px", fontSize: "13px" }}>
            Patient: {patientId}
          </span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* Paint Mode Toggle */}
          {!readOnly && <>
            <div style={{ display: "flex", background: "#f1f5f9", borderRadius: "6px", padding: "2px" }}>
              {["surface", "overall"].map((mode) => (
                <button key={mode}
                  onClick={() => setPaintMode(mode)}
                  style={{
                    padding: "4px 10px", borderRadius: "4px", border: "none",
                    background: paintMode === mode ? "white" : "transparent",
                    boxShadow: paintMode === mode ? "0 1px 3px rgba(0,0,0,0.12)" : "none",
                    cursor: "pointer", fontSize: "12px", fontWeight: paintMode === mode ? 600 : 400,
                    color: paintMode === mode ? "#0f172a" : "#64748b",
                    textTransform: "capitalize",
                  }}>
                  {mode}
                </button>
              ))}
            </div>
            <button onClick={undo} disabled={undoStack.length === 0}
              style={{ padding: "4px 10px", borderRadius: "6px",
                border: "1px solid #cbd5e1", background: "white", cursor: "pointer",
                fontSize: "12px", color: "#475569",
                opacity: undoStack.length === 0 ? 0.4 : 1 }}>
              ↩ Undo
            </button>
            <button onClick={saveChart}
              style={{ padding: "4px 12px", borderRadius: "6px",
                border: "none", background: "#2563eb", color: "white",
                cursor: "pointer", fontSize: "12px", fontWeight: 600 }}>
              Save
            </button>
          </>}
          {/* Save status */}
          <span style={{ display: "flex", alignItems: "center", gap: "4px",
            fontSize: "11px", color: statusColors[saveStatus] }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%",
              background: statusColors[saveStatus] }} />
            {statusLabels[saveStatus]}
          </span>
        </div>
      </div>

      <div style={{ display: "flex", gap: "0" }}>

        {/* ── Left: Chart Area ── */}
        <div style={{ flex: 1, padding: "16px", minWidth: 0 }}>

          {/* Condition palette */}
          {!readOnly && (
            <div style={{ marginBottom: "12px" }}>
              <ConditionPalette
                selectedCondition={selectedCondition}
                onSelect={setSelectedCondition}
              />
            </div>
          )}

          {/* Arch label + teeth */}
          <div style={{ background: "white", borderRadius: "8px",
            border: "1px solid #e2e8f0", padding: "12px" }}>
            <div style={{ textAlign: "center", fontSize: "11px", fontWeight: 600,
              color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em",
              marginBottom: "4px" }}>
              Maxillary (Upper)
            </div>
            {renderTeethRow(UPPER_TEETH, true)}

            <div style={{ borderTop: "2px dashed #e2e8f0", margin: "12px 0",
              position: "relative" }}>
              <span style={{ position: "absolute", top: "-9px", left: "50%",
                transform: "translateX(-50%)", background: "white",
                padding: "0 8px", fontSize: "10px", color: "#94a3b8" }}>
                MIDLINE
              </span>
            </div>

            <div style={{ textAlign: "center", fontSize: "11px", fontWeight: 600,
              color: "#94a3b8", textTransform: "uppercase", letterSpacing: "0.08em",
              marginBottom: "4px" }}>
              Mandibular (Lower)
            </div>
            {renderTeethRow(LOWER_TEETH, false)}
          </div>

          {/* Legend toggle */}
          <div style={{ marginTop: "10px" }}>
            <button onClick={() => setShowLegend(!showLegend)}
              style={{ background: "none", border: "none", cursor: "pointer",
                fontSize: "12px", color: "#64748b", padding: "4px 0" }}>
              {showLegend ? "▲" : "▼"} Color Legend
            </button>
            {showLegend && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                {Object.entries(CONDITION_COLORS).map(([cond, color]) => (
                  <div key={cond} style={{ display: "flex", alignItems: "center",
                    gap: "4px", fontSize: "11px", color: "#475569" }}>
                    <span style={{ width: "10px", height: "10px", borderRadius: "2px",
                      background: color, border: "1px solid rgba(0,0,0,0.1)" }} />
                    {cond}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Right: Detail Panel ── */}
        <div style={{ width: "280px", flexShrink: 0, borderLeft: "1px solid #e2e8f0",
          background: "white", overflowY: "auto" }}>
          <ToothDetailPanel
            toothNum={selectedTooth}
            toothState={selectedTooth ? (chart[selectedTooth] || defaultToothState(selectedTooth)) : null}
            onUpdateSurface={updateSurface}
            onUpdateOverall={updateOverall}
            onUpdateNotes={updateNotes}
          />
        </div>
      </div>
    </div>
  );
}
