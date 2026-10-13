from pathlib import Path
from xml.etree import ElementTree as E
from html import escape
import zipfile, json

OUT=Path('docs/architecture/drawio'); OUT.mkdir(parents=True,exist_ok=True)
NAVY='#23394D'; BLUE='#2878A6'; GREEN='#35745B'; PURPLE='#7857A0'; GRAY='#657787'
class Page:
 def __init__(self,name,w=1500,h=1050):
  self.name=name; self.model=E.Element('mxGraphModel',dx='1500',dy='1000',grid='1',gridSize='10',guides='1',tooltips='1',connect='1',arrows='1',fold='1',page='1',pageScale='1',pageWidth=str(w),pageHeight=str(h),math='0',shadow='0')
  self.root=E.SubElement(self.model,'root');E.SubElement(self.root,'mxCell',id='0');E.SubElement(self.root,'mxCell',id='1',parent='0');self.n=1
 def cell(self,label,x,y,w,h,style='',parent='1'):
  self.n+=1; id=f'n{self.n}'
  c=E.SubElement(self.root,'mxCell',id=id,value=label,style='html=1;whiteSpace=wrap;fontFamily=Helvetica;fontSize=15;fontColor='+NAVY+';'+style,vertex='1',parent=parent)
  E.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'});return id
 def text(self,label,x,y,w,h=35,size=15,color=NAVY):return self.cell(label,x,y,w,h,f'text;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize={size};fontColor={color};')
 def title(self,t,sub,w=1400):self.text('<b>'+t+'</b>',40,25,w,45,28);self.text(sub,40,77,w,40,15,GRAY)
 def box(self,label,x,y,w=220,h=80,color='#EAF2F8',shape='rounded=1;arcSize=12;'):
  return self.cell(label,x,y,w,h,f'{shape}fillColor={color};strokeColor=#78909C;spacing=10;')
 def group(self,label,x,y,w,h,color='#71869A',fill='#FAFCFD',aws=None):
  # Explicit group boundary. Children remain separate editable shapes inside it.
  style=f'rounded=0;fillColor={fill};strokeColor={color};strokeWidth=2;verticalAlign=top;align=left;spacingTop=12;spacingLeft=14;fontStyle=1;'
  if aws:style+=f'shape=mxgraph.aws4.group;grIcon=mxgraph.aws4.{aws};spacingLeft=45;'
  return self.cell(label,x,y,w,h,style)
 def icon(self,name,label,x,y,color='#ED7100'):
  id=self.cell('',x,y,64,64,f'shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{name};fillColor={color};strokeColor=#FFFFFF;')
  self.text(label,x-46,y+68,156,58,14);return id
 def edge(self,a,b,label='',color=BLUE,dashed=False,points=None,style=''):
  self.n+=1;c=E.SubElement(self.root,'mxCell',id=f'n{self.n}',value=label,edge='1',parent='1',source=a,target=b,style=f'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;endFill=1;strokeWidth=2;strokeColor={color};fontColor={color};fontFamily=Helvetica;fontSize=13;labelBackgroundColor=#FFFFFF;'+('dashed=1;' if dashed else '')+style)
  g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
  if points:
   ar=E.SubElement(g,'Array',attrib={'as':'points'})
   pairs=list(zip(points[::2],points[1::2])) if isinstance(points[0],(int,float)) else points
   for x,y in pairs:E.SubElement(ar,'mxPoint',x=str(x),y=str(y))
  return c
 def line(self,x1,y1,x2,y2,label='',dashed=False,arrow=True):
  self.n+=1;c=E.SubElement(self.root,'mxCell',id=f'n{self.n}',value=label,edge='1',parent='1',style=f'html=1;endArrow={"block" if arrow else "none"};strokeColor={BLUE};strokeWidth=2;dashed={int(dashed)};fontSize=14;labelBackgroundColor=#FFFFFF;')
  g=E.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'});E.SubElement(g,'mxPoint',x=str(x1),y=str(y1),attrib={'as':'sourcePoint'});E.SubElement(g,'mxPoint',x=str(x2),y=str(y2),attrib={'as':'targetPoint'})
 def note(self,t,x,y,w,h=75):return self.box(t,x,y,w,h,'#FFF7DF','rounded=0;')

pages=[]
p=Page('Local Development Architecture',1500,950);p.title('Local Development Architecture','HELP University parking system • Build and test on one computer before using AWS.')
p.group('YOUR COMPUTER',290,155,1160,590,GREEN,'#F5FAF7')
admin=p.box('<b>Administrator</b><br>Uses a web browser',45,215,200)
source=p.box('<b>Test images or video</b><br>Real camera added later',45,440,200,95)
ui=p.box('<b>Admin website</b><br>Vue frontend',340,215)
api=p.box('<b>Application API</b><br>Login, vehicles and access rules',665,215,240,95)
db=p.box('<b>Local MySQL</b><br>Vehicles, permits and records',1100,215,250,100,shape='shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=15;')
conn=p.box('<b>Camera connector</b><br>Chooses a useful frame',340,440)
ai=p.box('<b>Plate reader</b><br>Simulated result first<br>Partner AI model later',665,440,240,100)
sim=p.box('<b>Gate and screen simulator</b><br>No real gate opens in early tests',1090,455,270,90)
p.edge(admin,ui,'Open website');p.edge(ui,api,'Local HTTP / JSON');p.edge(api,db,'Read / save data')
p.edge(source,conn,'Image frames');p.edge(conn,api,'Send frame',points=[620,480,620,340,785,340]);p.edge(api,ai,'Read plate');p.edge(ai,api,'Plate + confidence',color=GREEN,style='exitX=1;exitY=0.2;entryX=1;entryY=0.8;',points=[965,460,965,290]);p.edge(api,conn,'Reply to decision poll',color=GREEN,points=[580,350,450,350]);p.edge(conn,sim,'Apply fresh decision',color=GREEN,points=[450,585,1225,585]);
p.note('The connector applies the decision to the simulator and reports the result. It will handle real devices later.',345,615,1000,65)
p.note('<b>No EC2 or RDS yet.</b> Use local MySQL. Keep passwords out of source code. Python is proposed for the API; confirm this with the partner.',45,790,1400,80)
pages.append(('01_Local_Development_Architecture.drawio',[p]))

p=Page('AWS Network and Data Flow',1700,1150);p.title('AWS Network and Data Flow','Proposed FYP pilot • One application server • Private database • Solid arrows show request paths.',1600)
p.group('HELP UNIVERSITY',30,280,270,630,GRAY,'#F8FAFC')
camera=p.box('<b>Camera</b><br>Local video stream',65,350,200,80)
gate=p.box('<b>Gate + display</b><br>Local device connection',65,760,200,85)
connector=p.box('<b>Campus connector</b><br>Uploads selected frames<br>Polls for the decision',65,530,200,110)
p.edge(camera,connector,'RTSP on campus LAN');p.edge(connector,gate,'Apply fresh decision',color=GREEN)
admin=p.box('<b>Admin browser</b><br>Staff login',50,140,210,85)
net=p.box('Internet',345,280,140,100,'#F1F5F9','ellipse;')
p.edge(admin,net,'HTTPS 443');p.edge(connector,net,'Outbound HTTPS 443',points=[325,585,325,390,415,390])
p.group('AWS CLOUD — one chosen region',530,135,1130,790,'#232F3E','#FFFFFF','group_aws_cloud')
p.group('VPC — private AWS network  |  example: 10.0.0.0/16',570,285,1050,580,'#8C4FFF','#FAF8FE','group_vpc')
igw=p.icon('internet_gateway','Internet gateway',700,170,'#8C4FFF')
p.edge(net,igw,'Internet route',points=[495,330,495,177]);
p.group('PUBLIC APP SUBNET — Zone A\n10.0.1.0/24',610,335,390,390,'#7AA116','#F7FBEF','group_subnet')
p.group('PRIVATE DATABASE SUBNETS\nDB subnet group spans two zones',1080,335,495,450,'#00A4A6','#F0FAFA','group_subnet')
ec2=p.icon('ec2','<b>EC2 application server</b><br>Public IP address',760,415)
p.text('HTTPS website + API<br>Plate reader on same host',665,575,290,55,15)
p.text('<b>App security group</b><br>Inbound: HTTPS 443 only<br>No public SSH / database port',650,650,310,60,14)
rds=p.icon('rds','<b>RDS for MySQL</b><br>Zone A • no public IP',1210,435,'#C925D1')
p.text('Vehicles, permits and events<br><b>DB security group:</b><br>3306 from app security group only',1130,575,370,75,14)
p.box('Zone B private subnet<br>Reserved in DB subnet group<br>No standby database in this pilot',1120,680,405,75,'#FFFFFF','dashed=1;rounded=0;')
p.edge(igw,ec2,'HTTPS 443',points=[652,295,792,295]);p.edge(ec2,rds,'MySQL TLS 3306',points=[1040,447,1040,467])
p.text('Public route table: 0.0.0.0/0 → Internet gateway',615,795,435,50,13)
p.text('DB route table: VPC local routes only<br>No direct Internet route',1100,805,455,45,13)
p.note('<b>Return traffic:</b> replies use the same client connection. The campus connector asks for decisions; AWS does not open a new connection to the gate.',35,960,795,100)
p.note('<b>Pilot limits:</b> one EC2 and one RDS instance are not highly available. Use a domain and a trusted TLS certificate on EC2. See page 2 for passwords, permissions and monitoring.',860,960,795,100)
aws1=p

p=Page('AWS Security and Support Services',1600,1150);p.title('AWS Security and Support Services','Same EC2 server as page 1 • Dashed arrows show permissions / configuration, not camera traffic.',1500)
p.group('AWS CLOUD — regional services sit outside your VPC subnets',40,140,1510,865,'#232F3E','#FFFFFF','group_aws_cloud')
p.group('VPC / public app subnet',95,365,440,370,'#8C4FFF','#FAF8FE','group_vpc')
ec=p.icon('ec2','<b>EC2 application server</b><br>Uses an instance role',245,470)
role=p.icon('identity_and_access_management','<b>IAM instance role</b><br>Only needed permissions',245,200,'#DD344C')
p.edge(role,ec,'Attach role',PURPLE,True)
egress=p.box('<b>Outbound service calls</b><br>HTTPS 443 through<br>the Internet gateway',640,485,235,100,'#F1F5F9')
p.edge(ec,egress,'AWS API requests')
secrets=p.icon('secrets_manager','<b>Secrets Manager</b><br>Database login details',1050,215,'#DD344C')
cw=p.icon('cloudwatch','<b>CloudWatch</b><br>Logs, metrics and alerts',1050,415,'#E7157B')
ssm=p.icon('systems_manager','<b>Systems Manager</b><br>Server access without SSH',1050,615,'#E7157B')
s3=p.icon('s3','<b>S3 — optional</b><br>Private saved plate images',1050,815,'#7AA116')
for n,label,y in [(secrets,'Read secret',247),(cw,'Send logs',447),(ssm,'Agent connection',647),(s3,'Save images',847)]:p.edge(egress,n,label,points=[935,535,935,y])
p.note('Never give database passwords to the browser or camera. The app reads the secret using its instance role.',1240,200,260,120)
p.note('Install / configure the CloudWatch agent or app log shipping. Alerts do not appear automatically.',1240,400,260,120)
p.note('Install the SSM agent and allow outbound HTTPS. No inbound port 22 is needed.',1240,600,260,110)
p.note('Only retain images if approved. Use private access, encryption and a deletion policy.',1240,800,260,110)
p.text('<b>RDS backups + encryption</b><br>Enable automatic backups and encryption.<br>Secrets Manager and RDS use KMS encryption.<br>A separate custom KMS key is optional.',105,780,710,110,16)
p.note('<b>Not required for this pilot:</b> NAT Gateway or private VPC endpoints (EC2 already has public outbound access). A load balancer + ACM certificate, private EC2 subnets, or Multi-AZ failover are later upgrades with extra design and cost.',45,1040,1500,80)
aws2=p;pages.append(('02_AWS_Network_and_Security_Architecture.drawio',[aws1,aws2]))

def exit_page():
 p=Page('Exit Process Flow',1550,1570)
 p.title('Exit Process Flow','Scan plate → show parking duration → open exit gate → save after passage.',1450)
 labels=[('Vehicle reaches exit',140),('Scan and read the number plate',270),('Find the latest open visit for this plate<br>Read the entry time',400),('Calculate parking duration<br>Current time minus entry time',540),('Show plate and parking duration<br>on the exit screen',680),('Open the exit gate',820),('Vehicle passed the gate?',960),('Save exit time and final duration<br>Mark this visit as EXITED in the database',1150),('Close gate when safe',1330)]
 nodes=[]
 for text,y in labels:
  nodes.append(p.box(text,540,y,400,90,'#FFF1CD' if y==960 else '#EAF2F8','rhombus;' if y==960 else 'rounded=1;'))
 for i in range(len(nodes)-1):p.edge(nodes[i],nodes[i+1],'Yes' if i==6 else '')
 fault=p.box('No confirmed passage:<br>keep the visit open<br>Record attempt / fault only',1070,950,360,115,'#FCE8E4');p.edge(nodes[6],fault,'No / timeout')
 p.note('No permit, payment, blocked-status or guest-approval check at exit.<br>The entry lookup is only for calculating duration and finding the visit to update.',55,410,360,185)
 p.note('No matching entry?<br>Show “Duration unavailable” and still open the gate.<br>After passage, save the plate and exit time as an unmatched EXITED record.',1050,440,390,195)
 p.note('Plate unreadable or system unavailable?<br>Guard helps with the plate / manual exit.<br>Record confirmed exit when the system is available.',55,750,360,175)
 p.note('Guests and registered vehicles follow the same exit steps. Final duration = confirmed exit time minus entry time. Repeated passage reports must not save duplicate exits.',55,1450,1390,80)
 return p

def flow_page(exit_flow=False):
 if exit_flow:return exit_page()
 p=Page('Exit Process Flow' if exit_flow else 'Entrance and Guest Process Flow',1700,1720)
 p.title(p.name,'Save the parking record only after the vehicle passes the gate.',1600)
 def box(t,y,kind=False):return p.box(t,580,y,320,95,'#FFF1CD' if kind else '#EAF2F8','rhombus;' if kind else 'rounded=1;')
 start=box('Vehicle reaches exit' if exit_flow else 'Vehicle reaches entrance',145)
 read=box('Capture picture and read plate',290)
 clear=box('Plate clear and<br>system available?',435,True)
 check=box('Find an open parking visit<br>using the plate number' if exit_flow else 'Find plate in the vehicle list',590)
 found=box('Open visit found?' if exit_flow else 'Plate found?',745,True)
 rules=box('Exit checks passed?<br>Payment if required' if exit_flow else 'Entry allowed?<br>Not blocked; valid permission',915,True)
 opened=box('Request gate opening',1090)
 passed=box('Vehicle passed<br>the gate?',1250,True)
 saved=box('Save exit time and close the visit<br>Keep the guest / vehicle history' if exit_flow else 'Save entry time and open a parking visit',1430)
 manual=p.box('Keep gate closed<br>Guard checks / corrects the plate<br>Guard decides whether to open',1130,590,400,110,'#FFF7DF')
 approve=p.box('Guard opens<br>the gate?',1170,775,320,110,'#FFF1CD','rhombus;')
 guest=p.box('Mark this attempt as a guest visit<br>Use the plate confirmed by the guard<br>No guest record saved yet' if not exit_flow else 'Use the visit confirmed by the guard<br>If no visit exists, mark as unmatched exit',1130,965,400,110,'#FFF7DF')
 denied=p.box('Gate stays closed<br>No entry or exit record',1150,1415,360,95,'#FCE8E4')
 fault=p.box('No confirmed passage:<br>save attempt / fault only<br>Do not create a parking record',70,1235,370,115,'#FCE8E4')
 p.edge(start,read);p.edge(read,clear);p.edge(clear,check,'Yes');p.edge(clear,manual,'No',points=[1040,480,1040,645]);p.edge(check,found);p.edge(found,rules,'Yes');p.edge(found,manual,'No',points=[1030,790,1030,645]);p.edge(rules,opened,'Yes');p.edge(rules,manual,'No',points=[990,960,990,645]);p.edge(manual,approve);p.edge(approve,guest,'Yes');p.edge(approve,denied,'No',points=[1600,830,1600,1460]);p.edge(guest,passed,'Gate opened manually',points=[1060,1020,1060,1295]);p.edge(opened,passed);p.edge(passed,saved,'Yes');p.edge(passed,fault,'No / timeout')
 if not exit_flow:
  p.note('For a new plate admitted by the guard:<br><b>save the plate as Guest together with the entry record after passage.</b><br>Existing blocked or expired vehicles keep their original category.',70,800,380,205)
 else:
  p.note('Registered vehicles and guests use the same exit flow.<br>If no visit can be matched, save an unmatched exit for review after passage.<br>Never invent an earlier entry time.',70,800,380,205)
 p.note('Guard actions are recorded. A manual opening is not proof of passage. Use a passage sensor or explicit guard confirmation. Close the gate only when safe.',70,1570,1460,90)
 return p
pages.append(('03_Parking_System_Process_Flow.drawio',[flow_page(),flow_page(True)]))

def seq_page(mode):
 title={'entry':'Registered Vehicle Entry Sequence','guest':'Guest Entry with Guard Sequence','exit':'Vehicle and Guest Exit Sequence'}[mode]
 p=Page(title,1850,1580);p.title(title,'Attempt logs may be saved earlier. The parking entry / exit is saved only after confirmed passage.',1740)
 actors=[('Camera connector',170),('Application API',520),('Plate reader',870),('MySQL database',1220),('Guard / gate + sensor',1630)]
 for label,x in actors:p.box('<b>'+label+'</b>',x-130,150,260,65);p.line(x,215,x,1410,dashed=True,arrow=False)
 messages=[(170,520,'Upload picture + unique attempt ID'),(520,870,'Read plate'),(870,520,'Return plate and confidence'),(520,1220,'Look up latest open visit and entry time (no status checks)' if mode=='exit' else 'Look up plate and entry permission')]
 if mode=='guest':
  messages += [(1220,520,'Plate not found: wait for guard'),(520,1630,'Show plate for guard to check / correct'),(1630,520,'Guard confirms plate and manual opening'),(1630,170,'Guard opens gate; connector records the action')]
 else:
  messages += [(1220,520,'Return entry time, or no matching entry' if mode=='exit' else 'Return vehicle and valid permission'),(520,170,'Calculate duration; send plate + duration for display' if mode=='exit' else 'Return fresh entry permission'),(170,1630,'Show duration and open exit gate' if mode=='exit' else 'Request gate opening once'),(1630,170,'Gate command result (not proof of passage)')]
 messages += [(1630,170,'Sensor or guard confirms vehicle has passed'),(170,520,'Report confirmed exit + unique passage ID' if mode=='exit' else 'Report confirmed entry + unique passage ID')]
 if mode=='guest':save='Save Guest plate + entry time + open visit + guard reference together'
 elif mode=='exit':save='Save exit time + final duration; mark visit EXITED'
 else:save='Save entry time and open parking visit'
 messages += [(520,1220,save),(1220,520,'Saved once; repeated passage reports do not duplicate records'),(520,170,'Confirm record saved')]
 for i,(a,b,label) in enumerate(messages):p.line(a,280+i*85,b,280+i*85,str(i+1)+'. '+label,dashed=a>b)
 note='No guard opening or no confirmed passage: no guest entry is saved. Saving a guest does not give permanent automatic entry permission.' if mode=='guest' else ('No status or payment checks. Missing entry: show Duration unavailable and still open; save an unmatched EXITED record after passage. Unreadable plate / outage: guard assists.' if mode=='exit' else 'Unknown plate: use the Guest Entry sequence. Failed checks need guard review. No confirmed passage means no entry record.')
 p.note(note+' Gate safety sensors remain active.',45,1460,1750,85)
 return p
pages.append(('04_Vehicle_Access_Message_Sequence.drawio',[seq_page('entry'),seq_page('guest'),seq_page('exit')]))

p=Page('Parking Database Diagram',1650,1200);p.title('Parking Database Diagram','Initial logical design • PK = unique record ID • FK = link to another record • 1 / many labels show relationships.',1550)
def entity(name,fields,x,y,w=300):
 h=60+len(fields)*25
 return p.cell('<b>'+name+'</b><hr>'+ '<br>'.join(escape(f) for f in fields),x,y,w,h,'rounded=0;fillColor=#F4F8FC;strokeColor=#57748F;align=left;verticalAlign=top;spacing=12;fontSize=15;')
owner=entity('Vehicle owners',['PK Owner ID','Name','Student / staff / visitor','Student or staff reference'],55,155)
veh=entity('Vehicles',['PK Vehicle ID','FK Owner ID','Unique plate number','Vehicle description','Blocked / archived'],455,155)
permit=entity('Parking permits',['PK Permit ID','FK Vehicle ID','Start date / end date','Permit status'],875,155)
payment=entity('Payment records',['PK Payment ID','FK Permit ID','Amount / payment status','Payment reference'],1275,155)
visitor=entity('Visitor approvals',['PK Visitor request ID','FK Vehicle ID','FK Reviewing admin ID','Visit start / end','Approval status'],455,510)
events=entity('Plate readings',['PK Reading ID','FK Camera ID','FK Vehicle ID (may be empty)','Unique device event key','Time / plate / confidence','Model / image reference'],875,480)
camera=entity('Cameras',['PK Camera ID','Gate name','Entry / exit direction','Enabled'],1275,510)
admin=entity('Admin users',['PK Admin ID','Email / password hash','Role / active status'],55,510)
audit=entity('Admin change log',['PK Log ID','FK Admin ID','Action / changed record','Time'],55,900)
decision=entity('Access decisions',['PK Decision ID','FK Reading ID (unique)','Allow / deny / review','Reason / expiry time','Gate command result'],875,870)
passage=entity('Entry and exit records',['PK Passage ID','FK Decision ID (unique)','Entry / exit / time','How passage was confirmed'],1275,890)
p.edge(owner,veh,'1 → many');p.edge(veh,permit,'1 → many');p.edge(permit,payment,'1 → many');p.edge(veh,visitor,'1 → many');p.edge(veh,events,'1 → many',points=[800,410,1025,410]);p.edge(camera,events,'1 → many');p.edge(events,decision,'1 → 0 or 1');p.edge(decision,passage,'1 → 0 or 1');p.edge(admin,audit,'1 → many');p.edge(admin,visitor,'1 → many reviews');
p.note('An unknown plate can have a reading without a linked vehicle. An allowed command is not proof of entry: save entry / exit only after confirmed passage.',440,925,360,160)
pages.append(('05_Parking_Database_Entity_Relationship_Diagram.drawio',[p]))

def save(file,ps):
 root=E.Element('mxfile',host='app.diagrams.net',agent='HELP FYP architecture',version='26.0.0',type='device')
 for i,p in enumerate(ps):d=E.SubElement(root,'diagram',id=f'page-{i+1}',name=p.name);d.append(p.model)
 E.indent(root);E.ElementTree(root).write(OUT/file,encoding='utf-8',xml_declaration=True)
for file,ps in pages:
 if file.startswith(('03_', '04_')) or not (OUT/file).exists():save(file,ps)
 else:
  existing=E.parse(OUT/file).getroot().findall('diagram')
  for page,old in zip(ps,existing):page.model=old.find('mxGraphModel')
save('HELP_Parking_System_All_Diagrams.drawio',[p for _,ps in pages for p in ps])
# Structural checks: every connector references an existing native cell.
for file in OUT.glob('*.drawio'):
 for d in E.parse(file).getroot().findall('diagram'):
  cells=d.findall('.//mxCell');ids=[c.get('id') for c in cells]
  assert len(ids)==len(set(ids)),file
  for c in cells:
   for attr in ['source','target']:
    if c.get(attr):assert c.get(attr) in ids,(file,attr)
 print(file.name, 'OK')
links=[]
for i,p in enumerate([p for _,ps in pages for p in ps]):
 config={'xml':E.tostring(p.model,encoding='unicode'),'toolbar':'zoom','lightbox':False,'editable':False,'auto-fit':True,'resize':True}
 html='<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'self\' data:; script-src \'self\' \'unsafe-inline\' \'unsafe-eval\'; style-src \'self\' \'unsafe-inline\'; connect-src \'self\'; img-src \'self\' data:;"><style>body{margin:18px;font-family:Arial;background:white}.mxgraph{width:100%;border:0}</style>'
 div='<div class="mxgraph" data-mxgraph="'+escape(json.dumps(config),quote=True)+'"></div>'
 html+='<script src="viewer-static.min.js"></script><script>fetch("aws4.xml").then(r=>r.text()).then(t=>{const doc=new DOMParser().parseFromString(t,"text/xml");for(const n of doc.querySelectorAll("shapes > shape")){mxStencilRegistry.addStencil("mxgraph.aws4."+n.getAttribute("name").replace(/ /g,"_"),new mxStencil(n));}document.body.insertAdjacentHTML("beforeend",'+json.dumps(div)+');GraphViewer.processElements();});</script>'
 Path(f'tmp/drawio/page-{i}.html').write_text(html,encoding='utf-8')
 links.append(f'<p><a href="page-{i}.html">{p.name}</a></p>')
Path('tmp/drawio/index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Local diagram review</h1>'+''.join(links),encoding='utf-8')
