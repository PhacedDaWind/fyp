import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';
const out = 'C:/Users/USER/VisualStudioCodeProjects/fyp/outputs/fyp-gantt';
const wb = Workbook.create();
const s = wb.worksheets.add('FYP Gantt');
const col = n => { let t=''; for(;n;n=Math.floor((n-1)/26)) t=String.fromCharCode(65+(n-1)%26)+t; return t; };
const serial = d => (Date.parse(d+'T00:00:00Z')-Date.UTC(1899,11,30))/86400000;
const tasks = [
['Research','Confirm scope and project proposal','2026-09-10','2026-09-25','Task'],
['Research','Search and critically review 10–12 articles','2026-09-14','2026-10-02','Task'],
['Research','Write literature synthesis and research gap','2026-09-22','2026-10-04','Task'],
['Research','Submit literature review assignment','2026-10-05','2026-10-05','Milestone'],
['Requirements','Consult stakeholders and document requirements','2026-10-06','2026-10-30','Task'],
['Requirements','Refine literature review and performance criteria','2026-10-06','2026-11-27','Task'],
['Design','Design system and deployment architecture','2026-11-02','2026-11-20','Task'],
['Design','Design database, access rules and admin workflows','2026-11-09','2026-11-27','Task'],
['Design','Complete requirements and design documentation','2026-11-30','2026-11-30','Milestone'],
['AI model','Obtain partner model and establish baseline','2026-10-12','2026-10-30','Task'],
['AI model','Arrange image collection and dataset permissions','2026-10-19','2026-11-06','Task'],
['AI model','Collect and annotate Malaysian plate images','2026-11-09','2026-12-18','Task'],
['AI model','Split dataset and prepare augmentation pipeline','2026-12-14','2026-12-31','Task'],
['AI model','Adapt and fine-tune the provided model','2027-01-04','2027-02-05','Task'],
['AI model','Evaluate outdoor accuracy and analyse errors','2027-02-08','2027-02-26','Task'],
['AI model','Complete model evaluation against 90% target','2027-02-28','2027-02-28','Milestone'],
['Development','Refine the admin interface prototype','2026-09-18','2026-10-09','Task'],
['Development','Develop backend, database and admin login','2026-12-01','2027-01-15','Task'],
['Development','Implement vehicle, permit and visitor management','2027-01-04','2027-02-05','Task'],
['Development','Implement payment status and entry-exit records','2027-01-25','2027-02-19','Task'],
['Integration','Prepare camera and barrier test environment','2027-01-18','2027-02-12','Task'],
['Integration','Integrate recognition with parking access workflow','2027-03-01','2027-03-19','Task'],
['Integration','Run pilot and resolve integration issues','2027-03-22','2027-03-30','Task'],
['Integration','Complete integrated parking system','2027-03-31','2027-03-31','Milestone'],
['Testing','Prepare 20+ test cases and outdoor trial plan','2027-03-08','2027-03-26','Task'],
['Testing','Run functional and repeated outdoor trials','2027-04-01','2027-04-16','Task'],
['Testing','Fix defects, retest and evaluate performance','2027-04-19','2027-04-26','Task'],
['Reporting','Write methods, implementation and results chapters','2026-11-02','2027-04-23','Task'],
['Reporting','Prepare final report, demonstration and presentation','2027-04-19','2027-04-29','Task'],
['Reporting','Complete testing and final project review','2027-04-30','2027-04-30','Milestone']
];
const first=10, last=first+tasks.length-1, weeks=34, endCol=col(9+weeks);
s.showGridLines=false; s.tabColor='#244C3C';
s.getRange(`A1:${endCol}${last+11}`).format.font={name:'Arial',size:10,color:'#26392E'};
s.getRange(`A1:${endCol}${last+11}`).format.rowHeight=25;
s.getRange(`A1:${endCol}${last+11}`).format.verticalAlignment='center';
const widths=[44,115,345,90,90,65,83,87,130];
widths.forEach((w,i)=>s.getRange(`${col(i+1)}1:${col(i+1)}${last}`).format.columnWidthPx=w);
s.getRange(`J1:${endCol}${last}`).format.columnWidthPx=48;
s.getRange('A2').values=[['HELP University ANPR Parking System Gantt Chart']];
s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#203D2C'};
s.getRange('A2').format.rowHeight=32;
s.getRange('A3').values=[['Proposed schedule: September 2026 to April 2027. Intermediate dates are planning estimates, not confirmed deadlines.']];
s.getRange('A4').values=[['Edit amber cells: task details, start/end dates, type and progress. Duration, date checks and weekly bars update automatically.']];
s.getRange('A5').values=[['Progress is blank until entered. Green = planned work; purple M = milestone. Each column represents a Monday–Sunday week.']];
s.getRange('A6').values=[['Timeline starts (Monday)']]; s.getRange('D6').values=[[serial('2026-09-07')]];s.getRange('D6').setNumberFormat('dd mmm yy');s.getRange('D6').format.fill='#FFF1CC';
s.getRange('F6').values=[['34 weeks shown; change D6 to move the timeline. Dates do not automatically reschedule dependent tasks.']];
s.getRange(`A9:I9`).values=[['ID','Phase','Task / deliverable','Start','Finish','Days','Type','Progress','Date check']];
s.getRange(`A9:${endCol}9`).format.fill='#244C3C';
s.getRange(`A9:${endCol}9`).format.font={name:'Arial',size:10,bold:true,color:'#FFFFFF'};
s.getRange(`A9:${endCol}9`).format.rowHeight=35;s.getRange(`A9:${endCol}9`).format.horizontalAlignment='center';
for(let j=0;j<weeks;j++){
 const c=col(10+j);
 s.getRange(`${c}9`).formulas=[[j===0?'=$D$6':`=${col(9+j)}9+7`]];
 s.getRange(`${c}9`).setNumberFormat('dd mmm');
 if(j===0 || new Date(Date.UTC(2026,8,7+j*7)).getUTCMonth()!==new Date(Date.UTC(2026,8,7+(j-1)*7)).getUTCMonth()){
  s.getRange(`${c}8`).formulas=[[`=TEXT(${c}9,"mmm yy")`]];
  s.getRange(`${c}8`).format.font={name:'Arial',size:10,bold:true,color:'#244C3C'};
 }
}
const colors={'Research':'#DBE8F3','Requirements':'#E9E5F3','Design':'#E9E5F3','AI model':'#E1EFD9','Development':'#FBEACF','Integration':'#FBEACF','Testing':'#F4DEDA','Reporting':'#E4E8EA'};
tasks.forEach(([phase,task,start,finish,type],i)=>{
 const r=first+i;
 s.getRange(`A${r}:I${r}`).values=[[i+1,phase,task,serial(start),serial(finish),null,type,null,null]];
 s.getRange(`B${r}:E${r}`).format.fill='#FFF7E3';s.getRange(`G${r}:H${r}`).format.fill='#FFF7E3';
 s.getRange(`A${r}:B${r}`).format.fill=colors[phase];
 s.getRange(`A${r}:${endCol}${r}`).format.rowHeight=34;
 s.getRange(`C${r}`).format.wrapText=true;
 s.getRange(`D${r}:E${r}`).setNumberFormat('dd mmm yy');
 s.getRange(`H${r}`).setNumberFormat('0%');
 s.getRange(`I${r}`).formulas=[[`=IF(OR(D${r}="",E${r}=""),"Missing dates",IF(OR(NOT(ISNUMBER(D${r})),NOT(ISNUMBER(E${r}))),"Invalid date",IF(E${r}<D${r},"Finish < start",IF(AND(G${r}="Milestone",D${r}<>E${r}),"Use one date",IF(OR(D${r}<$J$9,E${r}>$${endCol}$9+6),"Outside view","OK")))))`]];
 s.getRange(`F${r}`).formulas=[[`=IF(OR(I${r}="OK",I${r}="Outside view"),IF(G${r}="Milestone",0,E${r}-D${r}+1),"")`]];
 const formulas=[];
 for(let j=0;j<weeks;j++){const c=col(10+j); formulas.push(`=IF(AND(OR($I${r}="OK",$I${r}="Outside view"),$D${r}<=${c}$9+6,$E${r}>=${c}$9),IF($G${r}="Milestone","M",1),"")`);}
 s.getRange(`J${r}:${endCol}${r}`).formulas=[formulas];
 if(i===0||tasks[i-1][0]!==phase) s.getRange(`A${r}:${endCol}${r}`).format.borders={top:{style:'thin',color:'#AAB9AE'}};
 if(type==='Milestone')s.getRange(`C${r}`).format.font={name:'Arial',size:10,bold:true,color:'#674486'};
});
s.getRange(`G${first}:G${last}`).dataValidation={rule:{type:'list',values:['Task','Milestone']}};
s.getRange(`H${first}:H${last}`).dataValidation={rule:{type:'decimal',operator:'between',formula1:0,formula2:1}};
s.getRange(`J${first}:${endCol}${last}`).setNumberFormat(';;;@');
s.getRange(`J${first}:${endCol}${last}`).format.horizontalAlignment='center';
s.getRange(`J${first}:${endCol}${last}`).conditionalFormats.add('cellIs',{operator:'equal',formula:1,format:{fill:'#6F9C7F'}});
s.getRange(`J${first}:${endCol}${last}`).conditionalFormats.add('containsText',{text:'M',format:{fill:'#76568F',font:{color:'#FFFFFF',bold:true}}});
s.getRange(`I${first}:I${last}`).conditionalFormats.addCustom(`I${first}<>"OK"`,{fill:'#FCE6E0',font:{color:'#A43529',bold:true}});
s.freezePanes.freezeRows(9);s.freezePanes.freezeColumns(3);
const notes=[
['Schedule basis','Assignment deadline: 5 October 2026. Objective milestones: design November 2026, AI February 2027, integration March 2027, testing April 2027.'],
['Planning assumptions','Month-only targets are placed at month-end. Final report and presentation dates are proposed; confirm university deadlines and semester breaks.'],
['Data and model','Model training depends on partner weights/code and usable Malaysian images. Keep the evaluation set separate from training and tuning.'],
['Dependencies','Requirements inform design; prepared data enables training; evaluated AI and backend enable integration; integration enables end-to-end trials.'],
['Testing targets','Proposed: 90% complete-plate accuracy, response time below 3 seconds, and 95% operational reliability. Agree measurement definitions with the supervisor.'],
['Editing','Use real Excel dates in Start and Finish. Set milestones to the same start/end date. Days are inclusive calendar days; milestones have zero duration.'],
['Progress','Enter 0%–100% yourself. It is a tracking field only; green bars show the planned schedule, not actual completion.'],
['More tasks','Insert and copy a complete task row within the schedule to preserve formulas and formatting, then change its ID, details and dates.'],
['Source','Project proposal and objectives supplied in this conversation. All detailed task dates are suggested planning allocations.']
];
notes.forEach(([label,text],i)=>{const r=last+2+i;s.getRange(`A${r}`).values=[[label]];s.getRange(`A${r}`).format.font={name:'Arial',size:10,bold:true};s.getRange(`C${r}`).values=[[text]];});
wb.recalculate();
// Check the formula response to an edit and restore the original input.
const before=s.getRange('J10').values[0][0];
s.getRange('D10').values=[[serial('2026-09-21')]];wb.recalculate();
if(s.getRange('J10').values[0][0]!=='' || s.getRange('L10').values[0][0]!==1) throw new Error('Date edit did not update Gantt');
s.getRange('D10').values=[[serial('2026-09-10')]];wb.recalculate();
if(before!==1 || s.getRange('F10').values[0][0]!==16) throw new Error('Duration verification failed');
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#SPILL!',options:{useRegex:true,maxResults:20},summary:'Formula errors'})).ndjson);
console.log((await wb.inspect({kind:'table',range:'FYP Gantt!D10:L13',include:'values,formulas',tableMaxRows:4,tableMaxCols:9,maxChars:2500})).ndjson);
await fs.mkdir(out,{recursive:true});
await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/HELP-University-FYP-Gantt.xlsx`);
for(const [name,range] of [['gantt-preview','A1:Q16'],['gantt-later','AB8:AQ39']]){
 const image=await wb.render({sheetName:s.name,range,scale:1,format:'png'});
 await fs.writeFile(`${out}/${name}.png`,new Uint8Array(await image.arrayBuffer()));
}
console.log('Saved editable Gantt workbook.');
