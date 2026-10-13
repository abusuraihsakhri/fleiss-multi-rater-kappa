// Fleiss' generalized kappa and its null-hypothesis variance.
// No network requests or third-party runtime dependencies.
export function calculateKappa(matrix) {
  if (!Array.isArray(matrix) || matrix.length === 0 ||
      !Array.isArray(matrix[0]) || matrix[0].length < 2) {
    throw new Error("Provide a nonempty matrix with at least two categories.");
  }
  const categories = matrix[0].length;
  let raters = null;
  const totals = Array(categories).fill(0);
  for (const [i, row] of matrix.entries()) {
    if (!Array.isArray(row) || row.length !== categories) {
      throw new Error("Every subject must have the same number of categories (row " + (i+1) + ").");
    }
    if (row.some(value => !Number.isSafeInteger(value) || value < 0)) {
      throw new Error("Counts must be non-negative safe integers (row " + (i+1) + ").");
    }
    const n = row.reduce((sum, value) => sum + value, 0);
    if (raters === null) raters = n;
    if (raters !== n) throw new Error("Every subject must have the same number of raters.");
    row.forEach((count, j) => { totals[j] += count; });
  }
  if (raters < 2) throw new Error("At least two raters are required per subject.");
  const N = matrix.length;
  const p = totals.map(total => total / (N * raters));
  const observed = matrix.reduce((sum, row) =>
    sum + row.reduce((s, v) => s + v * (v-1), 0) / (raters * (raters-1)), 0) / N;
  const expected = p.reduce((sum, v) => sum + v*v, 0);
  const degenerate = Math.abs(1-expected) < 1e-12;
  const kappa = degenerate ? 1 : (observed - expected)/(1 - expected);
  let standard_error = null, z_score = null, p_value = null, inference_note = null;
  if (degenerate) inference_note = "Unanimous-agreement convention (chance agreement = 1); inference is undefined.";
  else if (N < 2) inference_note = "At least two independent subjects are needed for inference.";
  else {
    const p3 = p.reduce((sum, v) => sum + v*v*v, 0);
    const variance = 2*(expected + expected*expected - 2*p3) /
      (N*raters*(raters-1)*(1-expected)**2);
    if (variance > 0) {
      standard_error = Math.sqrt(variance);
      z_score = kappa/standard_error;
      // Numerically stable two-sided normal tail approximation.
      const x = Math.abs(z_score) / Math.SQRT2;
      // Hastings approximation to erfc; adequate for display and tests.
      const t = 1/(1+0.3275911*x);
      const erf = 1 - (((((1.061405429*t - 1.453152027)*t) +
        1.421413741)*t - 0.284496736)*t + 0.254829592)*t)*Math.exp(-x*x);
      p_value = Math.min(1, Math.max(0, 1-erf));
    } else inference_note = "Null variance is zero; z and p are undefined.";
  }
  const interpretation = kappa < 0 ? "Poor" : kappa <= .2 ? "Slight" :
    kappa <= .4 ? "Fair" : kappa <= .6 ? "Moderate" :
    kappa <= .8 ? "Substantial" : "Almost perfect";
  return {kappa,standard_error,z_score,p_value,observed_agreement:observed,
    chance_agreement:expected,n_subjects:N,n_raters:raters,n_categories:categories,
    interpretation,inference_note};
}

// RFC4180-like quoted CSV reader with consistent row sizes; no third-party parser.
export function parseCSV(text) {
  const src = String(text).replace(/^\uFEFF/, "");
  const rows = [];
  let row=[],field="",quoted=false;
  for (let i=0; i<src.length; i++) {
    const c=src[i];
    if (quoted) {
      if (c==='"' && src[i+1]==='"') {field+='"';i++;}
      else if (c==='"') quoted=false;
      else field+=c;
    } else if (c==='"' && field==="") quoted=true;
    else if (c===',') {row.push(field);field="";}
    else if (c==='\n') {row.push(field);rows.push(row);row=[];field="";}
    else if (c==='\r' && src[i+1]==='\n') {continue;}
    else if (c==='"') throw new Error("Unexpected quote in CSV field.");
    else field+=c;
  }
  if (quoted) throw new Error("Unclosed quoted CSV field.");
  if (field!=="" || row.length) {row.push(field);rows.push(row);}
  if (rows.length < 2) throw new Error("CSV requires a header and at least one subject.");
  const headings=rows[0].map(h=>h.trim());
  const cols=headings.map((h,i)=>({name:h,index:i,match:/^(?:cat|c|v)([1-9]\d*)$/i.exec(h)}))
    .filter(v=>v.match).sort((a,b)=>Number(a.match[1])-Number(b.match[1]));
  if (cols.length<2 || new Set(cols.map(v=>Number(v.match[1]))).size!==cols.length) {
    throw new Error("CSV must have distinct cat1, cat2, ... columns (c1/v1 also accepted).");
  }
  const matrix=rows.slice(1).filter(r=>r.some(v=>v.trim()!=="")).map((r,i)=>{
    if (r.length!==headings.length) throw new Error("CSV row "+(i+2)+" has the wrong number of columns.");
    return cols.map(col=>{
      const cell=r[col.index].trim();
      if (!/^\d+$/.test(cell)) throw new Error("CSV row "+(i+2)+", "+col.name+": non-negative integer required.");
      const count=Number(cell);
      if (!Number.isSafeInteger(count)) throw new Error("CSV count exceeds safe integer range.");
      return count;
    });
  });
  if (!matrix.length) throw new Error("CSV has no subject data.");
  return {matrix,categories:cols.map(v=>v.name)};
}
