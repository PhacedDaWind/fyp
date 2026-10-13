import fs from 'node:fs/promises';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const path='C:/Users/USER/VisualStudioCodeProjects/fyp/outputs/fyp-gantt/HELP-University-FYP-Gantt.xlsx';
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path));
const sheet=wb.worksheets.getItem('FYP Gantt');
const changes=new Map([
  ['Arrange image collection and dataset permissions','Plan plate photo collection and get permission'],
  ['Collect and annotate Malaysian plate images','Collect Malaysian plate photos and label them'],
  ['Split dataset and prepare augmentation pipeline','Set aside test photos and make varied training copies'],
]);
const data=sheet.getRange('C10:C38').values;
const found=[];
for(let i=0;i<data.length;i++){
  const replacement=changes.get(data[i][0]);
  if(!replacement)continue;
  const row=i+10;
  const before=await wb.render({sheetName:sheet.name,range:`A${row}:Q${row}`,scale:1,format:'png'});
  await fs.writeFile(`C:/Users/USER/VisualStudioCodeProjects/fyp/tmp/fyp-gantt/before-row-${row}.png`,new Uint8Array(await before.arrayBuffer()));
  sheet.getRange(`C${row}`).values=[[replacement]];
  found.push([row,replacement]);
}
if(found.length!==3)throw new Error(`Expected three task names, found ${found.length}`);
wb.recalculate();
for(const [row,label] of found)if(sheet.getRange(`C${row}`).values[0][0]!==label)throw new Error('Task name not saved');
const image=await wb.render({sheetName:sheet.name,range:'A18:Q25',scale:1,format:'png'});
await fs.writeFile('C:/Users/USER/VisualStudioCodeProjects/fyp/tmp/fyp-gantt/simplified-tasks-preview.png',new Uint8Array(await image.arrayBuffer()));
await(await SpreadsheetFile.exportXlsx(wb)).save(path);
console.log(JSON.stringify(found));
