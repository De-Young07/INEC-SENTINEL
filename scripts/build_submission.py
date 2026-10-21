"""Build the two-page NEXUS submission from the current evidence export."""
import json, csv
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
ROOT=Path(__file__).resolve().parents[1]
with (ROOT/'Deliverables/NEXUS_LGA_Evidence.csv').open(encoding='utf-8', newline='') as handle:
    rows=list(csv.DictReader(handle))
geo=json.loads((ROOT/'data/sentinel_boundaries.json').read_text())
lookup={r['shapeID']:r for r in rows}
out=ROOT/'Deliverables/NEXUS_SENTINEL_Submission.pdf'
c=canvas.Canvas(str(out),pagesize=(612,792));c.setTitle('NEXUS Team SENTINEL Digital Divide Submission');c.setAuthor('NEXUS Team')
ink=HexColor('#17313b');teal=HexColor('#157f75')
style=ParagraphStyle('body',fontName='Helvetica',fontSize=9.4,leading=13,textColor=ink)
def text(s,x,y,w=524,size=9.4):
 st=ParagraphStyle('p',parent=style,fontSize=size,leading=size*1.38)
 p=Paragraph(s,st);_,h=p.wrap(w,700);p.drawOn(c,x,y-h);return y-h

def heading(s,y):
 c.setFillColor(teal);c.setFont('Helvetica-Bold',12);c.drawString(44,y,s);return y-12

def footer(page):
 c.setStrokeColor(HexColor('#ccd6d6'));c.line(44,36,568,36)
 c.setFillColor(ink);c.setFont('Helvetica',8);c.drawString(44,23,'NEXUS Team | DSN Bootcamp Geospatial Hackathon | 21 October 2026');c.drawRightString(568,23,f'{page} / 2')

c.setFillColor(ink);c.setFont('Helvetica-Bold',22);c.drawString(44,748,'SENTINEL')
y=text('Mapping Nigeria’s digital divide through connectivity evidence and public-service locations',44,734,size=12)
y=text('<b>NEXUS Team</b> — Quadri Adebisi, Glory Akanbi,<br/>Gboyega Pelumi Stephen and Neneh Precious Egbo-Egbo',44,y-9,size=10)
y=text('We combine the supplied Ookla extract with LGA/state boundaries, health facilities and schools to identify where verification is needed and plan affordable field visits.',44,y-10)
y=heading('Final national evidence map',y-24)
# Draw the same simplified LGA polygons and classifications as the application.
colors={'Insufficient evidence':'#aab5a8','Poor observed performance':'#c16c58','Review performance':'#cfaa60','Lower observed concern':'#589b89'}
maptop=y-8; scale=29
for f in geo['features']:
 r=lookup[f['properties']['shapeID']];g=f['geometry'];polys=[g['coordinates']] if g['type']=='Polygon' else g['coordinates']
 c.setFillColor(HexColor(colors[r['evidence_status']]));c.setStrokeColor(HexColor('#f5f7f2'));c.setLineWidth(.2)
 for poly in polys:
  path=c.beginPath()
  for ring in poly:
   for i,(lon,lat,*_) in enumerate(ring):
    px=138+(lon-2.7)*scale;py=maptop-(14-lat)*scale
    (path.moveTo if i==0 else path.lineTo)(px,py)
   path.close()
  c.drawPath(path,stroke=1,fill=1,fillMode=0)
legend_y=maptop-306
for i,(name,fill) in enumerate(colors.items()):
 x=44+(i%2)*265; yy=legend_y-(i//2)*17;c.setFillColor(HexColor(fill));c.rect(x,yy-7,9,9,fill=1,stroke=0);c.setFillColor(ink);c.setFont('Helvetica',8.5);count=sum(r['evidence_status']==name for r in rows);c.drawString(x+15,yy-5,f'{name} ({count})')
y=text('774 LGAs. Grey means missing evidence, not no service. Categories describe historical LGA averages, not current coverage, ward performance or election outcomes.',44,legend_y-37,size=8.7)
y=heading('From source records to decisions',y-20)
y=text('<b>1.</b> Standardize coordinates; match tile coordinates to LGA polygons: 9,209 of 9,234 records match, 25 remain excluded. <b>2.</b> Aggregate unweighted tile means and test totals. <b>3.</b> Assign state by largest polygon overlap in an equal-area projection; all 774 exceed the 95% review threshold. <b>4.</b> Spatially join health and education records; keep missing observations unknown. <b>5.</b> Screen upload/latency, then rank budget-limited verification visits.',44,y)
y=text('<b>Interactive map:</b> <link href="https://inec-sentinel-omega.vercel.app/" color="#157f75">inec-sentinel-omega.vercel.app</link><br/><b>Code:</b> <link href="https://github.com/De-Young07/INEC-SENTINEL" color="#157f75">github.com/De-Young07/INEC-SENTINEL</link>',44,y-10,size=9)
assert y>40, y
footer(1);c.showPage()
y=heading('External datasets and matching evidence',748)
y=text('<b>geoBoundaries:</b> 774 LGA polygons plus state/FCT boundaries provide administrative context. Assignments use geometry and stable IDs rather than names alone.<br/><b>GRID3 health facilities v3.0:</b> 41,778 records; 6,004 missing/empty geometries excluded. 35,772 of 35,774 usable records match LGAs.<br/><b>HOT OpenStreetMap education:</b> 6,327 of 6,329 usable records match LGAs. These are education locations, not verified polling units.',44,y)
y=text('Sources: <link href="https://www.geoboundaries.org/" color="#157f75">geoBoundaries</link>; <link href="https://data.humdata.org/dataset/a1e3e4bc-3699-4fe1-bd17-b38f4e7108d2" color="#157f75">GRID3 via HDX</link>; <link href="https://production-raw-data-api.s3.amazonaws.com/ISO3/NGA/education_facilities/hotosm_nga_education_facilities_osm_gpkg.zip" color="#157f75">HOT OSM education extract</link>. Supplied Ookla file: Nigeria Ookla.gpkg. Source counts and matching rules are retained in the audit.',44,y-8,size=8.5)
y=heading('Three findings and actions',y-25)
y=text('<b>1  A large observation gap.</b> 234 of 774 LGAs (30.2%) have no matched tile observations. <b>Action:</b> prioritize first measurements in these LGAs rather than labelling them blackouts.',44,y)
y=text('<b>2  Public services sit inside those gaps.</b> The 234 LGAs contain 10,308 matched GRID3 health records and 411 education records. <b>Action:</b> verify actual sites with local service managers and use them to organize repeated connectivity tests. These are source records, not confirmed offline facilities or beneficiary counts.',44,y-12)
y=text('<b>3  Weak performance needs stronger samples.</b> Madobi (Kano), Ezza South (Ebonyi), Doguwa (Kano), Rafi (Niger) and Edu (Kwara) are the five poor-performance LGAs under our screening rule. Each has only one observed tile; 355 of 540 observed LGAs have fewer than ten. Edu shows 15.129 Mbps download but 0.084 Mbps upload in that tile. <b>Action:</b> test across locations, times and carriers before proposing infrastructure; do not judge upload readiness from download speed alone.',44,y-12)
y=heading('Transparent scoring and an actionable workflow',y-25)
y=text('Score = 100 x [0.70 x clamp((2.5 - upload Mbps)/2.5) + 0.30 x clamp((latency ms - 50)/200)], with each clamp restricted to 0-1. Scores below 35 indicate lower concern, 35 to below 65 need review, and 65 or more indicate poor observations. Thresholds are pilot assumptions, not validated BVAS requirements. Unknown areas receive visit priority 75, not a risk score.',44,y)
y=text('Users search by LGA or state, hover for connectivity and sample details, inspect matching quality, and allocate equal-cost field visits within a budget. A separate shared monitoring workflow records authorized reports and tracks incident acknowledgment and recovery. SMS/email sending is currently disabled.',44,y-10)
y=heading('Limits and the next validation step',y-25)
y=text('The supplied extract’s period and mobile/fixed provenance remain unverified; the notebook’s Q4 2024 download does not establish them. Samples are uneven and tile means are unweighted. Facility records may overlap or be outdated. Population, settlement and socioeconomic layers are not yet validated, so we do not claim population-normalized deprivation, causes of failure, real-time nationwide coverage or verified polling-unit readiness. Next: validate source provenance and operational sites, then repeat field measurements before recommending capital spending.',44,y)
assert y>48, y
footer(2);c.save();print(out)
