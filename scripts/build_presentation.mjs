// Rebuild with the Codex bundled artifact-tool. Set C360_ARTIFACT_MODULE and
// C360_PRESENTATION_SKILL to the installed module and presentation skill paths.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
const root=process.cwd();
const skill=process.env.C360_PRESENTATION_SKILL;
const modulePath=process.env.C360_ARTIFACT_MODULE;
if (!skill || !modulePath) throw new Error('Set C360_PRESENTATION_SKILL and C360_ARTIFACT_MODULE');
const {Presentation,PresentationFile}=await import(pathToFileURL(modulePath).href);
const {resolvePresentationFont,applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const font=resolvePresentationFont({fontFamily:'Arial'});
const evidence=JSON.parse(await fs.readFile(path.join(root,'output/demo-evidence.json'),'utf8'));
const benchmark=JSON.parse(await fs.readFile(path.join(root,'output/benchmark.json'),'utf8'));
const build=path.join(root,'tmp/deck');
await fs.mkdir(build,{recursive:true});
const deck=Presentation.create({slideSize:{width:1280,height:720}});
const ink='#142A43',muted='#51627A',teal='#087F8C';
function text(slide,value,x,y,w,h,size=28,color=ink,bold=false){
 const box=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 box.text=value; box.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none'}; return box;
}
function slide(title,subtitle=''){
 const s=deck.slides.add();s.background.fill='#F7F9FC';
 text(s,title,72,52,1136,90,44,ink,true);
 if(subtitle) text(s,subtitle,72,151,1136,58,23,muted);
 text(s,`Customer 360  /  DS-001  /  Synthetic demonstration`,72,667,1020,24,15,muted);
 text(s,String(deck.slides.items.length),1170,665,40,25,16,muted);
 s.speakerNotes.textFrame.setText('Sources: user-supplied Case Study – DS-001.pdf; project source code and docs; output/demo-evidence.json, generated from DuckDB run '+evidence.metadata.run_id+'. All business measures are fictional.');
 return s;
}
function line(s,n,title,body,y){text(s,n,72,y,55,55,32,teal,true);text(s,title,152,y,1040,45,30,ink,true);text(s,body,152,y+53,1030,62,24,muted);}
let s=deck.slides.add();s.background.fill=ink;
text(s,'Customer 360',80,190,1100,105,76,'#FFFFFF',true);
text(s,'Analytics & Business Intelligence',84,311,1100,70,39,'#B9DFE1');
text(s,'DS-001 technical presentation',84,440,1040,50,28,'#FFFFFF');
text(s,'Reproducible synthetic-data implementation',84,510,1040,40,24,'#B9DFE1');
s.speakerNotes.textFrame.setText('The case study is implemented as a local Python/Streamlit project. The demo uses fictional data and does not claim enterprise deployment or measured 500-million-record capacity.');

s=slide('Project scope','A runnable local platform with explicit production boundaries');
text(s,'1,800',72,243,500,90,70,teal,true);text(s,'fictional customers',76,338,500,45,28,ink);
text(s,'36,000',685,243,500,90,70,teal,true);text(s,'generated orders before quality defects',688,338,500,75,28,ink);
text(s,'48 branches in 8 countries',76,451,1020,48,31,ink,true);
text(s,'January 2024 to August 2026. Eleven source extracts.\nThe enterprise target remains a separate capacity acceptance test.',76,520,1100,100,27,muted);

s=slide('Data pipeline','A complete source snapshot becomes a validated, traceable warehouse');
line(s,'01','Canonical source contracts','CRM, ERP, orders, payments, digital activity, support and campaigns.',225);
line(s,'02','Cleaning and reconciliation','Typed values, exact duplicates, conflicting IDs, dates, joins and payment checks.',355);
line(s,'03','Atomic publication','DuckDB facts and dimensions publish only after a successful build.',485);

s=slide('Data quality is observable','Deliberate order defects verify the handling of common source problems');
const orderQuality=evidence.quality.find(r=>r.source==='pos_orders');
const qchart=s.charts.add('bar',{position:{left:80,top:240,width:730,height:360},categories:['Duplicate rows','Invalid values','Integration rejects'],series:[{name:'Orders',values:[orderQuality.duplicate_rows,orderQuality.invalid_rows,orderQuality.integration_rejected],fill:teal}],barOptions:{direction:'column',grouping:'clustered'},hasLegend:false,dataLabels:{showValue:true,position:'outEnd'},yAxis:{numberFormatCode:'0'}});
applyPresentationChartFont(qchart,{fontFamily:font});
text(s,'Every source has row accounting and a SHA-256 fingerprint.',850,260,335,150,29,ink,true);
text(s,'Rejected records remain inspectable. A conflicting key fails the build.',850,450,335,140,25,muted);

s=slide('Revenue performance','September 2025 to August 2026, all countries and sales channels');
text(s,'$'+(evidence.metrics.revenue/1e6).toFixed(2)+'M',75,237,335,100,66,teal,true);
text(s,'synthetic net sales',80,347,330,42,27,ink);
text(s,evidence.metrics.buyers.toLocaleString('en-US')+' buyers\n'+(evidence.metrics.margin*100).toFixed(1)+'% gross margin',80,435,330,95,28,muted);
const revenueChart=s.charts.add('line',{position:{left:430,top:228,width:780,height:380},categories:evidence.monthly.map(r=>new Date(r.period).toLocaleString('en-US',{month:'short',year:'2-digit',timeZone:'UTC'})),series:[{name:'Revenue (USD thousands)',values:evidence.monthly.map(r=>Math.round(r.revenue/1000)),fill:teal}],hasLegend:false,yAxis:{numberFormatCode:'0'},lineOptions:{smooth:false}});
applyPresentationChartFont(revenueChart,{fontFamily:font});text(s,'Monthly revenue, rounded USD thousands',510,609,650,30,20,muted);

s=slide('Customer segmentation','All observed purchases through 31 August 2026');
const schart=s.charts.add('bar',{position:{left:75,top:235,width:740,height:380},categories:evidence.segments.map(r=>r.segment),series:[{name:'Customers',values:evidence.segments.map(r=>r.customers),fill:teal}],barOptions:{direction:'bar',grouping:'clustered'},hasLegend:false,dataLabels:{showValue:true,position:'outEnd'},xAxis:{numberFormatCode:'0'}});
applyPresentationChartFont(schart,{fontFamily:font});
text(s,'Fixed RFM thresholds',850,253,360,50,28,ink,true);
text(s,'Recency, frequency and monetary scores explain each profile.',850,326,340,105,25,muted);
text(s,'More than 90 inactive days is a churn proxy. Annualized gross profit is a value proxy.',850,458,350,150,25,muted);

s=slide('Analytical methods','Explicit units, baselines and limitations support interpretation');
line(s,'01','Retention and marketing','Buyer-set retention, mature purchase cohorts and campaign-level economics.',225);
line(s,'02','Exploratory statistics','Buyer-level Welch tests, Spearman correlations and median/MAD anomaly flags.',355);
line(s,'03','Forecast validation',`Three-month holdout. Selected model: ${evidence.diagnostics.model}. Approximate residual bands.`,485);

s=slide('Access and capacity','The tested local implementation is separate from the enterprise target');
text(s,'Local controls',76,244,500,50,32,teal,true);
text(s,'Viewer, analyst and admin roles\nSalted password hashes\nGuarded real-data mode\nLoopback-only default',76,320,500,240,29,ink);
text(s,'Deployment acceptance',690,244,500,50,32,teal,true);
text(s,'SSO, TLS and audit integration\nIncremental partitioned ingestion\nRegion-level authorization\n500M-record and concurrency tests',690,320,500,240,29,ink);
text(s,`Measured locally: ${benchmark.rows.toLocaleString('en-US')} valid sales rows. Median KPI query ${benchmark.timings.metrics.median_ms.toFixed(0)} ms across five sequential runs.`,76,602,1130,40,20,muted);

s=slide('Live demonstration','The repository includes the application, reports and operating instructions');
line(s,'01','Explore the dashboard','Filter sales, open a customer profile and compare product or branch performance.',225);
line(s,'02','Review evidence','Inspect campaign scope, forecast diagnostics, data quality and source provenance.',355);
line(s,'03','Generate the handover','Download executive PDFs and scoped CSVs. Rebuild the demo from the seed.',485);

const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(deck)).save(candidate);
for(let i=0;i<deck.slides.items.length;i++){
 const blob=await deck.export({slide:deck.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${i+1}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const finalPath=path.join(root,'output/presentation/customer360-technical.pptx');
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,
 pythonExecutable:process.env.C360_PYTHON,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:[font]},explicitTotalSlideCount:9,
 requiredNativeChartOwnerSlides:[4,5,6],materializeLiteralChartWorkbooks:true,
 verifyArtifactToolImport:true,receiptPath:path.join(build,'validation.json')});
console.log(JSON.stringify({finalPath,slides:deck.slides.items.length,result}));
