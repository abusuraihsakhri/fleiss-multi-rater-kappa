import {calculateKappa,parseCSV} from "./kappa.mjs";
const $=id=>document.getElementById(id);
const example=$("matrix").value;
let latest=null;
const show=(message,ok=false)=>{$("message").textContent=message;$("message").className=ok?"ok":""};
const fail=message=>{
  latest=null;$("export").disabled=true;
  for(const key of ["kappa","observed_agreement","chance_agreement","standard_error","p_value","interpretation"]){
    $(key).textContent="—";
  }
  $("subjects").textContent="Subjects: —";$("raters").textContent="Raters: —";
  $("categories").textContent="Categories: —";$("zscore").textContent="z: —";
  show(message);
};
const fmt=(value,digits=4)=>value==null?"N/A":Number(value).toFixed(digits);
function calculate(matrix) {
  latest=calculateKappa(matrix);
  for(const key of ["kappa","observed_agreement","chance_agreement","standard_error","p_value"]){
    $(key).textContent=fmt(latest[key],key==="p_value"?6:4);
  }
  $("interpretation").textContent=latest.interpretation;
  $("subjects").textContent="Subjects: "+latest.n_subjects;
  $("raters").textContent="Raters: "+latest.n_raters;
  $("categories").textContent="Categories: "+latest.n_categories;
  $("zscore").textContent="z: "+fmt(latest.z_score);
  $("note").textContent=(latest.inference_note?latest.inference_note+" ":"")+"The SE and p-value use the Fleiss–Nee–Landis (1979) asymptotic variance under H₀: κ = 0. They are not suitable for confidence intervals.";
  $("export").disabled=false;
  show("Calculated for "+latest.n_subjects+" subjects.",true);
}
$("calculate").addEventListener("click",()=>{
  try {calculate(JSON.parse($("matrix").value));}
  catch(e){fail(e instanceof Error?e.message:"Invalid input");}
});
$("example").addEventListener("click",()=>{$("matrix").value=example;$("csv").value="";$("calculate").click()});
$("csv").addEventListener("change",async e=>{
  const file=e.target.files?.[0];
  if(!file)return;
  if(file.size>1024*1024){fail("CSV exceeds 1 MB limit.");return;}
  try {
    const {matrix}=parseCSV(await file.text());
    $("matrix").value=JSON.stringify(matrix);
    calculate(matrix);
  } catch(err){fail(err instanceof Error?err.message:"Could not parse CSV");}
});
$("export").addEventListener("click",()=>{
  if(!latest)return;
  const names=Object.keys(latest);
  const data=[names.join(","),names.map(name=>{
    const str=latest[name]==null?"":String(latest[name]);
    return '"'+str.replaceAll('"','""')+'"';
  }).join(",")].join("\r\n")+"\r\n";
  const url=URL.createObjectURL(new Blob([data],{type:"text/csv;charset=utf-8"}));
  const a=document.createElement("a");a.href=url;a.download="fleiss-kappa-results.csv";a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
});
$("calculate").click();
