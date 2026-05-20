import { VitalsComponent } from './vitals';

/** Fabrică un VitalSign de test */
function makeVital(type: string, value: number, daysAgo = 0) {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return {
    id: Math.random().toString(),
    patient_id: 'p1',
    vital_type: type,
    value,
    unit: 'bpm',
    recorded_at: d.toISOString(),
    notes: null,
  };
}

describe('VitalsComponent — logică business', () => {
  let component: VitalsComponent;
  // ApiService minimal (nu facem HTTP în aceste teste)
  const apiSpy = jasmine.createSpyObj('ApiService', ['get']);

  beforeEach(() => {
    component = new VitalsComponent(apiSpy as any);
    // Setăm date direct, ocolim ngOnInit / HTTP
    component.vitals = [
      makeVital('pulse', 72, 3),
      makeVital('pulse', 80, 2),
      makeVital('pulse', 68, 1),
      makeVital('temperature', 36.6, 1),
      makeVital('temperature', 37.2, 0),
      makeVital('weight', 75, 5),
    ];
    component.loading = false;
  });

  // ── selectedTypeInfo ──────────────────────────────────────────────────────

  it('should return correct type info for default selectedType (pulse)', () => {
    expect(component.selectedType).toBe('pulse');
    const info = component.selectedTypeInfo;
    expect(info.key).toBe('pulse');
    expect(info.unit).toBe('bpm');
    expect(info.label).toBe('Puls');
  });

  it('should return correct type info after selectType()', () => {
    component.selectType('temperature');
    expect(component.selectedTypeInfo.key).toBe('temperature');
    expect(component.selectedTypeInfo.unit).toBe('°C');
  });

  // ── selectType ────────────────────────────────────────────────────────────

  it('selectType should update selectedType', () => {
    component.selectType('weight');
    expect(component.selectedType).toBe('weight');
  });

  it('selectType should rebuild chart (chart series not empty)', () => {
    component.selectType('pulse');
    expect(component.chart).toBeDefined();
    expect(component.chart.series).toBeDefined();
  });

  // ── getChartData ──────────────────────────────────────────────────────────

  it('getChartData should return only vitals of requested type', () => {
    const data = component.getChartData('pulse');
    expect(data.length).toBe(3);
    data.forEach(d => expect(typeof d.y).toBe('number'));
  });

  it('getChartData should return empty array for unknown type', () => {
    const data = component.getChartData('nonexistent');
    expect(data).toEqual([]);
  });

  it('getChartData should sort by date ascending', () => {
    const data = component.getChartData('pulse');
    // valorile sunt 72 (3 zile în urmă), 80 (2 zile), 68 (ieri) — ordine cronologică
    expect(data[0].y).toBe(72);
    expect(data[1].y).toBe(80);
    expect(data[2].y).toBe(68);
  });

  it('getChartData returns x as formatted string', () => {
    const data = component.getChartData('pulse');
    data.forEach(d => expect(typeof d.x).toBe('string'));
  });

  // ── recentVitals ──────────────────────────────────────────────────────────

  it('recentVitals should return only vitals of selectedType', () => {
    component.selectedType = 'pulse';
    expect(component.recentVitals.length).toBe(3);
    component.recentVitals.forEach(v => expect(v.vital_type).toBe('pulse'));
  });

  it('recentVitals should be sorted descending (newest first)', () => {
    component.selectedType = 'pulse';
    const rv = component.recentVitals;
    // Cel mai recent (daysAgo=1, valoare=68) trebuie să fie primul
    expect(rv[0].value).toBe(68);
    expect(rv[rv.length - 1].value).toBe(72);
  });

  it('recentVitals max 10 items', () => {
    // Adaugă 15 vitale de tip pulse
    component.vitals = Array.from({ length: 15 }, (_, i) => makeVital('pulse', 60 + i, i));
    component.selectedType = 'pulse';
    expect(component.recentVitals.length).toBe(10);
  });

  it('recentVitals empty when no vitals of selected type', () => {
    component.selectedType = 'oxygen_sat'; // nu avem în date
    expect(component.recentVitals).toEqual([]);
  });

  // ── vitalTypes config ─────────────────────────────────────────────────────

  it('should have 6 vital types defined', () => {
    expect(component.vitalTypes.length).toBe(6);
  });

  it('all vitalTypes should have key, label, unit, color', () => {
    component.vitalTypes.forEach(t => {
      expect(t.key).toBeTruthy();
      expect(t.label).toBeTruthy();
      expect(t.unit).toBeTruthy();
      expect(t.color).toMatch(/^#[0-9a-f]{6}$/i);
    });
  });
});
