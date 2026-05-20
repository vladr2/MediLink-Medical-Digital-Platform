import { MedicalRecordsComponent } from './medical-records';

function makeRecord(type: string, diagnosis = '', treatment = '', notes = '', analysis = '') {
  return {
    id: Math.random().toString(),
    patient_id: 'p1',
    doctor_id: 'd1',
    record_type: type,
    notes_encrypted: notes,
    diagnosis,
    treatment,
    analysis_result: analysis,
    created_at: new Date().toISOString(),
    has_anomaly: null,
    anomaly_notes: null,
  };
}

describe('MedicalRecordsComponent — logică business', () => {
  let component: MedicalRecordsComponent;
  const apiSpy = jasmine.createSpyObj('ApiService', ['get']);

  beforeEach(() => {
    component = new MedicalRecordsComponent(apiSpy as any);
    component.records = [
      makeRecord('consultatie', 'Hipertensiune arterială', 'Amlodipină 5mg'),
      makeRecord('analiza', '', '', '', 'Hemoleucogramă completă'),
      makeRecord('tratament', '', 'Paracetamol 500mg'),
      makeRecord('consultatie', 'Diabet tip 2', 'Metformină'),
    ];
    component.loading = false;
  });

  // ── Contoare per tip ──────────────────────────────────────────────────────

  it('countConsultatie should return number of consultations', () => {
    expect(component.countConsultatie).toBe(2);
  });

  it('countAnaliza should return number of analyses', () => {
    expect(component.countAnaliza).toBe(1);
  });

  it('countTratament should return number of treatments', () => {
    expect(component.countTratament).toBe(1);
  });

  it('counts should be 0 on empty records', () => {
    component.records = [];
    expect(component.countConsultatie).toBe(0);
    expect(component.countAnaliza).toBe(0);
    expect(component.countTratament).toBe(0);
  });

  // ── Filtrare (getter filtered) ────────────────────────────────────────────

  it('filtered with empty search returns all records', () => {
    component.searchText = '';
    expect(component.filtered.length).toBe(4);
  });

  it('filtered should match by diagnosis', () => {
    component.searchText = 'hipertensiune';
    expect(component.filtered.length).toBe(1);
    expect(component.filtered[0].diagnosis).toContain('Hipertensiune');
  });

  it('filtered should match by treatment', () => {
    component.searchText = 'paracetamol';
    expect(component.filtered.length).toBe(1);
  });

  it('filtered should match by analysis_result', () => {
    component.searchText = 'hemoleucogramă';
    expect(component.filtered.length).toBe(1);
  });

  it('filtered search is case-insensitive', () => {
    component.searchText = 'DIABET';
    expect(component.filtered.length).toBe(1);
    expect(component.filtered[0].diagnosis).toContain('Diabet');
  });

  it('filtered returns empty array for no match', () => {
    component.searchText = 'xyznonexistent';
    expect(component.filtered.length).toBe(0);
  });

  it('filtered should match by record type label (Consultație)', () => {
    component.searchText = 'consultație';
    expect(component.filtered.length).toBe(2);
  });

  // ── typeLabel ─────────────────────────────────────────────────────────────

  it('typeLabel should return Consultație for consultatie', () => {
    expect(component.typeLabel('consultatie')).toBe('Consultație');
  });

  it('typeLabel should return Analiză for analiza', () => {
    expect(component.typeLabel('analiza')).toBe('Analiză');
  });

  it('typeLabel should return Tratament for tratament', () => {
    expect(component.typeLabel('tratament')).toBe('Tratament');
  });

  it('typeLabel should return raw string for unknown type', () => {
    expect(component.typeLabel('unknown')).toBe('unknown');
  });

  // ── typeColor / typeBg / typeIcon ─────────────────────────────────────────

  it('typeColor returns correct color for each type', () => {
    expect(component.typeColor('consultatie')).toBe('#2563eb');
    expect(component.typeColor('analiza')).toBe('#0d9488');
    expect(component.typeColor('tratament')).toBe('#ea580c');
  });

  it('typeColor returns default color for unknown type', () => {
    expect(component.typeColor('necunoscut')).toBe('#2563eb');
  });

  it('typeBg returns background color for each type', () => {
    expect(component.typeBg('consultatie')).toBe('#eff6ff');
    expect(component.typeBg('analiza')).toBe('#f0fdfa');
    expect(component.typeBg('tratament')).toBe('#fff7ed');
  });

  it('typeIcon returns correct icon name', () => {
    expect(component.typeIcon('consultatie')).toBe('stethoscope');
    expect(component.typeIcon('analiza')).toBe('microscope');
    expect(component.typeIcon('tratament')).toBe('pill');
  });

  // ── toggleExpand ──────────────────────────────────────────────────────────

  it('toggleExpand should set expandedId', () => {
    component.toggleExpand('abc');
    expect(component.expandedId).toBe('abc');
  });

  it('toggleExpand should collapse when same id clicked again', () => {
    component.toggleExpand('abc');
    component.toggleExpand('abc');
    expect(component.expandedId).toBeNull();
  });

  it('toggleExpand should switch to new id', () => {
    component.toggleExpand('abc');
    component.toggleExpand('xyz');
    expect(component.expandedId).toBe('xyz');
  });
});
