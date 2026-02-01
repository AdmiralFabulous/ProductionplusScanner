# Optitex Batch Command Catalog

**Source**: help.optitex.com  
**Version**: O/25  
**Generated**: 2026-01-29

---

## SYNTAX RULES

1. Commands start with `@` symbol
2. Comments start with `;` semicolon
3. File names with spaces require quotes: `"C:\My Files\style.pds"`
4. Units are unitless - set with `@UNIT` at start
5. Silent mode: launch with `/s` flag: `PDS.exe /s /BATCH=script.bat`
6. End script with `@!` or `@EOF`

---

## PDS BATCH COMMANDS

### Control Flow

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@!` | `@EOF` | End batch execution | - |
| `@PAUSE` | `@-` | Pause execution | `/MSG=<text>` |
| `@?` | - | Continue after error | `[comment]` |
| `@EXIT` | `@EXI` | Close PDS | - |

### File Operations

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@NEW` | - | Start new clean pattern | - |
| `@OPEN` | `@OPE` | Open PDS/DSN/CUS file | `/FILE=<path>`, `/CUS` |
| `@MERGE` | `@MER` | Merge PDS files | `/FILE=`, `/SIZES={CUR\|MER\|BOTH}`, `/PREFIX=` |
| `@SAVE` | `@SAV` | Save style | `/FILE=`, `/FORMAT={PDS\|PDML\|DSN\|CUS}`, `/SEP`, `/XML={NO\|YES}` |

### Import/Export

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@IMPORT` | `@IMP` | Import file | `/FILE=`, `/FORMAT={DXF\|AAMA\|ASTM\|IGES\|HPGL\|...}`, `/UNIT=`, `/SCALE=` |
| `@EXPORT` | `@EXP` | Export PDS | `/FILE=`, `/FORMAT={DXF\|AAMA\|ASTM\|XML\|AI\|...}`, `/SEP`, `/STYLESHEET=` |

### Units & Settings

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@UNIT` | `@UNI` | Set working units | `/CM`, `/MM`, `/METER`, `/INCH`, `/FEET`, `/YARD` |
| `@SET` | - | Set INI preference | `/SECTION=`, `/KEYWORD=`, `/VALUE=` |

### Plotting & Output

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@PLOTTER` | `@PLO`, `@PLT` | Plot to file | `/FILE=`, `/FORMAT={HPGL\|HP2\|GERBER\|DMPL\|...}`, `/OPT={YES\|NO\|SHARED}`, `/OUTMAN={YES\|NO}`, `/COPIES=` |
| `@ARRANGE` | `@ARR` | Arrange to plotter | `/SCATTER`, `/WIDTH=`, `/GAP=`, `/LENGTH=`, `/ROT={YES\|NO}` |
| `@PRINT` | `@PRI` | Print to default printer | `/SCALE=`, `/PAGE` |

### Piece Operations

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@GLOBAL` | `@GLB` | Set global piece params | `/NAME=`, `/STYLE=`, `/CODE=`, `/QUANTITY=`, `/MATERIAL=`, `/TOOL=`, `/NTYPE=`, `/GBUF=`, `/GDIR=` |
| `@TRANSFORM` | `@TRA` | Transform pieces | `/NAME=`, `/ROTATE=`, `/FLIPVER`, `/FLIPHOR`, `/XSCALE=`, `/YSCALE=` |
| `@CLEAR` | - | Remove pieces from table | - |
| `@DELETEPIECE` | `@DELPIE` | Delete pieces | `/PIECE=`, `/PREFIX=` |
| `@ADDPREFIX` | `@ADDPRE` | Add prefix to names | `/PREFIX=` |
| `@DELPREFIX` | `@DELPRE` | Delete prefix | `/PREFIX=` |
| `@OPENHALF` | `@OPNHLF` | Open half pieces | - |
| `@RECTANGLE` | `@REC` | Create rectangle piece | `/LENGTH=`, `/WIDTH=`, `/NAME=`, `/CENTER={YES\|NO}` |

### Grading & Sizes

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@SIZES` | `@SIZ` | Control display sizes | `/ALL`, `/BASE`, `/ON=`, `/OFF=` |
| `@ONESIZE` | `@ONE` | Delete all sizes except one | `/SZ=<size>` |
| `@LOADSIZES` | `@LDSZS` | Load sizes | `/SIZE=` |
| `@APPLYRULESBYNAMES` | `@APPLYRULES` | Apply grading rules | `/SIZE=` |
| `@RENAMEBASESIZE` | `@RENMBS` | Rename base size | `/SIZE=` |
| `@DELETEONESIZE` | `@DELSZ` | Remove one size | `/SIZE=` |
| `@SETBASESIZE` | `@SETBASE` | Set base size | `/SIZE=` |
| `@INSERTMIDDLESIZE` | `@INSMIDSZ` | Insert size | `/FROMSIZE=`, `/NEWSIZE=`, `/RATIO=` |
| `@STACKGRADING` | `@STAGR` | Define grading stack | `/PIECE=`, `/PNT=`, `/BY={X\|Y\|ALL}` |
| `@SETGRADING` | `@GRADE` | Set piece grading | `/SIZE=`, `/PIECE=`, `/SZPIECE=` |
| `@SIZEVARIATION` | `@VAR` | Switch size variation | `/NAME=` |

### Rules & Libraries

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@RULES` | `@RULETABLE` | Import rule table | `/FILE=`, `/FM={IMPORT\|PDS}` |
| `@CLOSERULES` | `@CLSRL` | Close rules library | - |
| `@PNTASRUL` | - | Point names as rules | `/PIECE=` |
| `@REMOVERULESREF` | `@REMRULREF` | Remove rule refs | `/PIECE=` |

### Points & Geometry

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@MVPNT` | `@MOVEPNT`, `@MTM` | Move point | `/PNT=`, `/DX=`, `/DY=`, `/LSPNT=`, `/SHIFT` |
| `@MOVEPNTALONG` | `@MVALN` | Move along contour | `/PIECE=`, `/PNT=`, `/DISTANCE=`, `/CCW`, `/CW` |
| `@SETANGLE` | `@SETANG` | Set angle | `/PIECE=`, `/SIZE=`, `/POINT=`, `/ANGLE=` |
| `@ALTSTART` | `@AST` | Alternative start point | `/PNT=`, `/PIECE=`, `/ON`, `/OFF`, `/CW`, `/CCW` |
| `@ALLALTSTART` | `@ALLAST` | All alt start points | `/PIECE=`, `/ON`, `/OFF`, `/MINANG=`, `/MAXANG=` |
| `@POINTCLEANUP` | `@PNTCLUP` | Clean up points | `/TOL=`, `/MINLINE=`, `/DGR={Y\|N}`, `/INTERN={Y\|N}` |
| `@ASSIGNPOINTNAMES` | `@ASSPNTNMS` | Assign point names | `/PIECE=`, `/CNT=`, `/PRF=`, `/SUF=`, `/START=`, `/OVER` |
| `@REMOVENAMES` | `@REMNM` | Remove object names | `/PIECE=` |

### Seam Operations

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@RESEAM` | - | Reseam piece | `/PIECE=` |
| `@CHANGESEAM` | `@CHSEAM` | Change seam values | `/SEAM=`, `/PIECE=`, `/FRPNT=`, `/TOPNT=`, `/RESEAM={YES\|NO}`, `/MIN=`, `/MAX=`, `/CLEAR={YES}` |
| `@SWSEAM` | - | Switch seam to cut/sew | `/TYPE={SEW\|CUT}`, `/PIECE=` |
| `@SEWTOSEAM` | - | Create seam from sew | `/PIECE=` |

### Internals (Notches, Darts, Buttons, etc.)

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@CHNT` | `@CHNOTCH` | Change notch attrs | `/PIECE=`, `/ON={EXT\|INT\|SEAM\|ALL}`, `/DELETE`, `/LENGTH=`, `/WIDTH=`, `/ANGLE=`, `/TP=`, `/STP=`, `/CM=`, `/SCM=`, `/TL=`, `/STL=` |
| `@CHDR` | `@CHDART` | Change dart attrs | `/PIECE=`, `/DELETE`, `/DISTANCE=`, `/RADIUS=`, `/CM=`, `/SCM=`, `/TL=`, `/STL=` |
| `@CHBTN` | `@CHBUTTON` | Change button attrs | `/PIECE=`, `/DELETE`, `/TOCIR`, `/RADIUS=`, `/CM=`, `/SCM=`, `/TL=`, `/STL=` |
| `@CHCIR` | `@CHCIRCLE` | Change circle attrs | `/PIECE=`, `/DELETE`, `/TOBTN`, `/RADIUS=`, `/CM=`, `/SCM=`, `/TL=`, `/STL=` |
| `@CHCNT` | `@CHCONTOUR` | Change contour attrs | `/PIECE=`, `/DELETE`, `/CLOSED={YES\|NO\|ALL}`, `/CM=`, `/SCM=`, `/TL=`, `/STL=` |
| `@CHTXT` | `@CHTEXT` | Change text attrs | `/PIECE=`, `/DELETE`, `/SIZE=`, `/ANGLE=`, `/CM=`, `/SCM=`, `/BL={YES\|NO}` |

### Display Control

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@DISPLAY` | `@DIS` | Control display | `/TILT=`, `/GRPNT={Y\|N}`, `/POINT={Y\|N}`, `/TEXT={Y\|N}`, `/CONTOUR={Y\|N}`, `/NOTCH={Y\|N}`, `/DART={Y\|N}`, `/DRAW={Y\|N}`, `/CUT={Y\|N}` |

### Reports

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@REPORT` | `@REP` | Create Excel report | `/FILE=` |
| `@REPORTW` | `@REPW` | Report writer | `/TEMPLATE=`, `/TYPE={PDF\|XLSX\|CSV}`, `/OUTPUT=`, `/INPUT=` |

### 3D & Advanced

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@3DMODELLOAD` | `@3DM` | Load 3D model | `/FILE=`, `/MERGE` |
| `@CORRECTPIECESBYMAP` | `@CORBYMAP` | Correct by map zone | `/PIECE=` |
| `@CHANGEPIECEPROP` | `@PIEPR` | Change piece props | `/UNIQUE=`, `/PIECE=`, `/NAME=`, `/CODE=`, `/DESC=`, `/MATERIAL=`, `/QUALITY=`, `/QUANTITY=` |
| `@UNCHECK_EXCLUDE_IN_MARKER` | - | Remove exclude flag | - |

### DMC (Dynamic Measurement Chart)

| Command | Description | Key Parameters |
|---------|-------------|----------------|
| `@MTM_CREATE` | Import Excel to DMC, set sizes | `/LOAD_EXCEL_FILE=<path>`, `/SAVE_PDS_FILE=<path>` |

**Critical for Black Box**: The `@MTM_CREATE` command imports measurements from Excel into the Dynamic Measurement Chart system.

---

## MARKER BATCH COMMANDS

### Control Flow

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@!` | `@EOF` | End batch execution | - |
| `@EXIT` | `@EXI` | Close Marker | - |
| `@XEXIT` | `@XEX` | Stop, remove batch, close | - |
| `@PAUSE` | `@PAU` | Pause execution | `/MSG=` |
| `@?` | - | Continue after error | - |
| `@XOE` | - | Stop on error | - |

### File Operations

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@NEW` | - | New clean marker | `/NAME=` |
| `@OPEN` | `@OPE` | Open marker file | `/FILE=`, `/MERGE={NO\|YES}` |
| `@SAVE` | `@SAV` | Save marker | `/FILE=`, `/OVERWRITE={NO\|YES}`, `/FORMAT={MRK\|MRKML\|DSP8\|DSP9}`, `/LOG={NO\|YES}` |
| `@CLEAR` | `@CLE` | Clear marker table | - |
| `@UPDATE` | `@UPD` | Update styles from PDS | `/STYLE=`, `/FILE=`, `/MATERIAL=`, `/PIECE=`, `/CODE=`, `/GEOMETRY={NO\|YES}` |

### Units & Settings

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@UNIT` | `@UNI` | Set working units | `/CM`, `/MM`, `/METER`, `/INCH`, `/FEET`, `/YARD` |
| `@SET` | - | Set INI preference | `/SECTION=`, `/KEYWORD=`, `/VALUE=` |

### Marker Setup

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@MARKER` | `@MRK` | Set marker properties | `/NAME=`, `/LENGTH=`, `/HEIGHT=`, `/XO=`, `/XE=`, `/YO=`, `/YE=`, `/PLY=`, `/MATERIAL=`, `/LAYOUT={SINGLE\|TUBULAR\|FACED\|FOLDED}`, `/Weight=` |
| `@FLAW` | - | Add flaw area | `/LEFT=`, `/BOTTOM=`, `/RIGHT=`, `/TOP=` |
| `@BUMPLINE` | `@BUMP` | Add bump line | `/TYPE={HORIZONTAL\|VERTICAL\|RIGHTEDGE}`, `/LOCATION=` |
| `@BUMPLINEREMOVE` | `@BUMPREM` | Remove bump lines | `/TYPE={HORIZONTAL\|VERTICAL\|ALL}` |

### Design & Order

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@DESIGN` | `@DES` | Create marker order | `/FILE=`, `/SEAM={INT\|EXT\|CUT\|SEW\|BOTH}`, `/ORDER=`, `/STYLE=`, `/MATERIAL=`, `/SIZE=`, `/QUANTITY=`, `/RQ=`, `/SUBSTYLE=` |
| `@LEATHER` | - | Open leather file | `/FILE=` |
| `@SUBSTITUTE` | `@SUB` | Piece substitute | `/FILE=`, `/SEAM=`, `/CURRENTSTYLE=`, `/SOURCENAME=`, `/TARGETNAME=`, `/SSIZE=`, `/SIZE=`, `/MIRROR={YES\|NO}`, `/ROTATION=` |

### Import/Export

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@IMPORT` | `@IMP` | Import file | `/FILE=`, `/FORMAT={DXF\|AAMA\|ASTM\|GERB\|HPGL\|...}`, `/CLEAR={NO\|YES}`, `/UNIT=`, `/QUANTITY=`, `/BOX={YES\|NO}` |
| `@EXPORT` | `@EXP` | Export marker | `/FILE=`, `/FORMAT={DXF\|AAMA\|XML\|NST\|ALG\|AXML}` |

### Plotting & Output

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@PLOTTER` | `@PLO` | Plot to file | `/FILE=`, `/FORMAT={HPGL\|HP2\|GERBER\|DMPL\|...}`, `/XSCALE=`, `/YSCALE=`, `/OPT={YES\|NO\|SHARED}`, `/OUTMAN={YES\|NO}`, `/COPIES=`, `/BORDER={YES\|NO}`, `/PLOTEXT={YES\|NO}`, `/PLOTBUF={YES\|NO}` |
| `@PRINT` | `@PRI` | Print marker | `/FORMAT={SINGLE\|MULTIPLE\|FIXED}`, `/XSCALE=`, `/YSCALE=`, `/HEADER={YES\|NO}`, `/BORDER={YES\|NO}`, `/MARKER={YES\|NO}`, `/PIECES={YES\|NO}`, `/REPORT={YES\|NO}` |
| `@SNAPSHOT` | `@SNAP` | Create snapshot | `/FORMAT={PNG\|SVG}`, `/FILE=`, `/CROPX=`, `/CROPY=` |

### Nesting

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@NEST` | `@NES` | Auto nesting | See detailed table below |

#### @NEST Parameters (Critical for Automation)

| Parameter | Values | Description |
|-----------|--------|-------------|
| `/ALGORITHM=` | `QUICK`, `QUALITY`, `TEXTILE` (Nest++), `NESTER`, `COMPACTION`, `MATCH` (Match++), `ANT` (Nest++2), `PRO` (Nest++Pro), `LEATHER` | Nesting algorithm |
| `/TIME=` | minutes | Max nesting time |
| `/EFFLIM=` | 0-100 | Efficiency limit % |
| `/IDLETIME=` | minutes | Idle time between solutions |
| `/BUNDLES` | flag | Unify orientation in bundles |
| `/BUNDLESGROUP={YES\|NO}` | - | Nest according to bundles |
| `/UNLIMIT={YES\|NO}` | - | Unlimited marker X-size |
| `/RENEST={YES\|NO}` | - | Renest current pieces |
| `/IGNOREBUMP={YES\|NO}` | - | Ignore bump lines |
| `/AUTOSAVEMARKERS=` | file | Auto save markers |
| `/ALLOWFOLDED={YES\|NO}` | - | Allow folded on both sides |
| `/OSC={YES\|NO\|<area>}` | - | Optimize space for cutting |
| `/SIZESGROUP={YES\|NO}` | - | Group by sizes |
| `/HORZ_GROUP=` | 1-6 | Horizontal groups |
| `/BLOCK=` | 0-4 | Block algorithm (Nest++Pro) |

### Piece Operations

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@GLOBAL` | `@GLO` | Set global piece params | `/STYLE=`, `/SIZE=`, `/NAME=`, `/NUMBER=`, `/CODE=`, `/QUANTITY=`, `/MATERIAL=`, `/GBUF=`, `/GDIR=`, `/GMIR=`, `/GTILT=`, `/TOOL=` |
| `@TRANS` | `@TRA` | Transform piece | `/STYLE=`, `/SIZE=`, `/NAME=`, `/CODE=`, `/ROTATE=`, `/FLIP={YES\|NO}`, `/XSCALE=`, `/YSCALE=` |
| `@PLACE` | `@PLA` | Place piece on marker | `/PIECE=`, `/SIZE=`, `/TP={ONE\|ALL\|BUNDLES}`, `/FOLD={LF\|RG\|UP\|DW\|...}` |
| `@INSTANCEREMOVE` | - | Remove piece instances | `/ID=`, `/BUNDLE=` |
| `@DUPLICATE PLACEMENT` | - | Duplicate placement | - |

### Internals

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@GLOBALINTERNAL` | `@GLOINT` | Modify piece internals | `/RINTERNAL={NO\|BO\|DPP\|CONT\|CIRC\|LINEARCS}`, `/STYLE=`, `/SIZE=`, `/NAME=`, `/RTYPE=`, `/RMODE=`, `/NTOOL=`, `/NTYPE=`, `/NMODE=`, `/NANGLE=`, `/NDEPTHRAD=`, `/NWIDTH=` |
| `@CHTOOL` | `@CHT` | Change tool | `/PMODE={DRILL\|ADRILL\|NONE}`, `/MIN=`, `/MAX=` |
| `@ADJUSTDESCRIPTION` | `@ADJDESC` | Adjust description | `/MNSZ=`, `/MXSZ=`, `/PARBASELINE={YES\|NO}` |

### Display Control

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@DISPLAY` | `@DIS` | Show/hide attrs | `/DESC={YES\|NO\|SPCDZBM}`, `/TEXT={YES\|NO}`, `/TILT={YES\|NO}`, `/BUFFER={YES\|NO}`, `/INTERNAL={YES\|NO}`, `/NOTCH={YES\|NO}`, `/BUTTON={YES\|NO}` |

### Optimization

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@OPTIMIZEORDER` | `@OTO` | Cut/plot optimization | `/CCO={YES\|NO}`, `/StartTop={YES\|NO}`, `/ChooseSP={YES\|NO}`, `/ExtCutDir={OPT\|CW\|CCW}`, `/UseFrame={YES\|NO}`, `/AutoDetectSharedLine={YES\|NO}` |

### Reports

| Command | Alias | Description | Key Parameters |
|---------|-------|-------------|----------------|
| `@REPORT` | `@REP` | Excel report | `/FILE=`, `/TEMPLATE={0\|1\|2\|3}` |
| `@REPORTW` | `@REPW` | Report writer | `/TEMPLATE=`, `/TYPE={PDF\|XLSX\|CSV}`, `/OUTPUT=`, `/INPUT=` |
| `@SPREADINGMACHINEREPORT` | `@SPRMACHREP` | Spreading report | `/FILE=`, `/CUTFILE=`, `/SPRFILE=` |

### Print & Cut

| Command | Description | Key Parameters |
|---------|-------------|----------------|
| `@GENERATE_PDF` | Generate PDF | `/INPUT_FOLDER=`, `/OUTPUT_FILE=`, `/LANDSCAPE` |
| `@GENERATE_DXF` | Generate DXF | `/FILE=` |

---

## PLOTTER FORMAT CODES

| Code | Description |
|------|-------------|
| `HPGL` | HP Graphics Language |
| `HP2` | HPGL/2 |
| `HPTEC` | HPGL PlotTec |
| `HPGEN` | HPGL Generic |
| `HPLR` | HPGL Laser |
| `HPGLBAR` | HPGL Bar Code |
| `DMPL` | DMPL |
| `GERBER` | Gerber Cutter |
| `GERBCP` | Gerber Cutter for Plotter |
| `APGL` | Gerber Plotter |
| `AP700` | AP 700 Plotter |
| `ARISTO` | Aristomat Cutter |
| `ZUND` | Zund (PN, LC) Cutter |
| `EAST` | Eastman Cutter |
| `WILD` | Wild Cutter/Plotter |
| `WLDPL` | Wild Plotter |
| `CYBCUT` | Cybrid Cutter/Plotter |
| `CYBPL` | Cybrid Plotter |
| `LECTRA` | Lectra Flat Bed Plotter |
| `LECFP` | Lectra FlyPen |
| `LECTCT` | Lectra ISO Cut |
| `TAKA` | Takaoka Cutter |
| `CEDGE` | Cutting Edge |
| `MICRO` | MicroJet Plotter |
| `IEA` | IEA |
| `IOLS` | IOLS |
| `Mutoh` | Mutoh |
| `OptiJet` | OptiJet Printer/Plotter |

---

## EXPORT/IMPORT FORMAT CODES

| Code | Description |
|------|-------------|
| `DXF` | AutoCAD DXF |
| `AAMA` | AAMA/ASTM format |
| `ASTM` | ASTM format |
| `IGES` | IGES |
| `CADL` | CadKey |
| `XML` | XML |
| `AI` | Adobe Illustrator |
| `LEATHER` | Leather format |
| `VIRTEK` | Virtek |
| `NST` | Nest file |
| `ALG` | Algorithm file |
| `AXML` | AXML |
| `TIIP` | TIIP |
| `SPF` | SPF |
| `DFT` | cncKad |

---

## NESTING ALGORITHM CODES

| Code | Name | Description |
|------|------|-------------|
| `QUICK` | Quick | Fast, lower efficiency |
| `QUALITY` | Standard | Standard quality |
| `TEXTILE` | Nest++ | Advanced textile nesting |
| `NESTER` | External Nester | External nesting engine |
| `COMPACTION` | Compaction | Compaction algorithm |
| `MATCH` | Match++ | Pattern matching |
| `ANT` | Nest++2 | Enhanced Nest++ |
| `PRO` | Nest++Pro | Professional (best) |
| `LEATHER` | Leather | Leather-specific |

---

## ROTATION DIRECTION CODES

| Code | Degrees | Description |
|------|---------|-------------|
| `0` | All | All rotations allowed |
| `1` | None | No rotation |
| `2` | 180° | PI rotation only |
| `4` | 90° | PI/2 rotations |
| `8` | 45° | PI/4 rotations |

---

## BUFFER TYPE CODES

| Code | Description |
|------|-------------|
| `A` | Around (all sides) |
| `C` | Center |
| `U` | Up |
| `D` | Down |
| `L` | Left |
| `R` | Right |
| `UL` | Up-Left |
| `UR` | Up-Right |
| `DL` | Down-Left |
| `DR` | Down-Right |
| `ULR` | Up-Left-Right |
| `DLR` | Down-Left-Right |
| `RUD` | Right-Up-Down |
| `LUD` | Left-Up-Down |

---

## NOTCH TYPE CODES

| Code | Shape |
|------|-------|
| `T` | T-notch |
| `V` | V-notch |
| `I` | I-notch (slit) |
| `L` | L-notch |
| `U` | U-notch |
| `P` | Punch |
| `BOX` | Box |
| `CTL` | Cut to left |
| `CTC` | Cut to center |
| `CTB` | Cut to bottom |

---

## MODE CODES

| Code | Description |
|------|-------------|
| `DRAW` | Draw mode |
| `CUT` | Cut mode |
| `PUNCH` | Punch mode |
| `DRILL` | Drill mode |
| `ADRILL` | Auxiliary drill |
| `SEW` | Sew mode |
| `QUALITY` | Quality mode |
| `TRACK` | Track mode |
| `NONE` | None |

---

## SEAM TYPE CODES

| Code | Description |
|------|-------------|
| `INT` | Internal |
| `EXT` | External |
| `CUT` | Cut line |
| `SEW` | Sew line |
| `BOTH` | Both cut and sew |

---

## LAYOUT TYPE CODES

| Code | Description |
|------|-------------|
| `SINGLE` | Single ply |
| `TUBULAR` | Tubular fabric |
| `FACED` | Face-to-face |
| `FOLDED` | Folded |

---

## COMMAND LINE EXECUTION

### PDS Silent Mode
```batch
"C:\Program Files\Optitex\O25\PDS.exe" /s /BATCH="C:\scripts\process.bat"
```

### Marker Silent Mode
```batch
"C:\Program Files\Optitex\O25\Marker.exe" /s /BATCH="C:\scripts\nest.bat"
```

### With Specific File
```batch
"C:\Program Files\Optitex\O25\PDS.exe" /s /BATCH="script.bat" "C:\styles\jacket.pds"
```
