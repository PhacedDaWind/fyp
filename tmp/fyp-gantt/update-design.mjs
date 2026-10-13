import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const out='C:/Users/USER/VisualStudioCodeProjects/fyp/outputs/fyp-gantt';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(`${out}/HELP-University-FYP-Gantt.xlsx`));
const s=wb.worksheets.getItem('FYP Gantt');
const serial=d=>(Date.parse(d+'T00:00:00Z')-Date.UTC(1899,11,30))/86400000;
const names=['Design system and deployment architecture','Design database, access rules and admin workflows'];
const rows=s.getRange('C10:C38').values;
for(const name of names){
 const i=rows.findIndex(r=>r[0]===name);if(i<0)throw Error('Missing task: '+name);
 const r=i+10;s.getRange(`D${r}:E${r}`).values=[[serial('2026-09-26'),serial('2026-10-05')]];
}
// Preserve the established column widths after import.
const cols=['A','B','C','D','E','F','G','H','I'];
[44,115,345,90,90,65,83,87,130].forEach((w,i)=>s.getRange(`${cols[i]}1:${cols[i]}50`).format.columnWidthPx=w);
s.getRange('J1:AQ50').format.columnWidthPx=48;
wb.recalculate();
for(const name of names){const r=rows.findIndex(v=>v[0]===name)+10;
 if(s.getRange(`F${r}`).values[0][0]!==10||s.getRange(`N${r}`).values[0][0]!==1||s.getRange(`O${r}`).values[0][0]!=='')throw Error('Design schedule verification failed');
}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10}})).ndjson);
await(await SpreadsheetFile.exportXlsx(wb)).save(`${out}/HELP-University-FYP-Gantt.xlsx`);
const img=await wb.render({sheetName:s.name,range:'A9:Q19',scale:1,format:'png'});
await fs.writeFile(`${out}/design-update.png`,new Uint8Array(await img.arrayBuffer()));
