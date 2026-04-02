"""
Baked colormap look-up tables (256 x 3, uint8).
Generated from matplotlib colormaps so the runtime has no matplotlib dependency.
"""
import base64
import numpy as np


def _d(s: str) -> np.ndarray:
    return np.frombuffer(base64.b85decode(s), dtype=np.uint8).reshape(256, 3)

_VIRIDIS = _d(
    'L;+Mp0#-!?S49O`Mh99(2wX-AT}BIDM-5;{4q-<SV@DBWM-yd86lX{lXh;`nNEm8J8f-`#ZAct$N'
    'F8rTA8<$@aY!L^NF#JeBy~t7c1R|7NGNznDS1aKdPgjJM=g6tE__EXeMT^TMlyazGk-=jfJHTdMK'
    '^&(ID$kugG4%mL_35-J%mF(g+f1tLO_N>L54v>he1S#Kt+f^Mu<O0h(Ab)K1qo_N{K#9iakw=Jx+'
    '=|Pl`NHi#t(^J5q}}Q;RxOj5$?|IaZ7~Sd2JXj5k`0H(QN1T#YtejWu44HD8T1V2w0kjWc46Gh>Z'
    '1WR5arjxlDAF=vi3XpS&xjxcJDFKdo3Y>qB%jxKJFE^m%4aE>i;jx2GGEOL%4bB-%?jw^MJDt3-4'
    'caAD}jwyMLDSD16dyXi4jwpSOCw`76e~u@BjwXSQCW4M8f{rDFjwOVSC54V8hK?kMjw6VUBZ-b9i'
    'j5+RjUtSVB8`n9j*TIYjUkYYA(4zAl8hjdj3ASYAC!zAm5U#iiyxPZADD|DnTj8piXNMa9-N6Dor'
    'xcwi65VcAE1aIp@<)$haaMcAftvLq=q4-g(0SeBBzBSsDvY_gCwehC98rZtb!)3fhVnjD6W7huYW'
    '4Ae=M<nEwX(svwSbKd@;3qGPZg&ws|$Tc{jLtIJtK^x^_Febv?XvKfH55y>ddnaYVmxM!;`K!EQ>'
    'yZA`*!PQz<Z#A;H-X;j5%R>o&o$7Nc`WL(H&Uddu$%3x#5UuDZ)XUtq_&0B2ET5ir*aL-qB&{lQO'
    'RCm!+deKpQ(olcXPJz=+gw#uh)k%rfNQ>4+j@Ctx*F%%nL6z7*nAkp>**u-uJD}P*qS`m5+cv1%G'
    '^*S(t=urM-7m7;Ew$b&xZWwc-YC7_Ccxh%!rvps;33H1Aj;t%&EXx;;T+Q98`a_(*y0)5;~CxK7~'
    'kU<;^Y|R<QeDW8S3R4?ByHp<s9+l9rWfN_U0h?<{|s%BmL(k'
)

_GRAY = _d(
    '000010RaL60s{jB1Ox;H1qB8M1_uWR2nYxX2?+`c3JVJh3=9kn4Gj(s4i66x5D*X%5fKs+5)%^>6'
    'ciK{6%`g178e&67#J8C85tTH8XFrM92^`S9UUGX9v>ecARr(iAt53nA|oRsBqSsyB_$>%CMPE+C@'
    '3f?DJd!{Dl021EG#T7EiEoCE-x=HFfcGNF)=bSGBYzXG&D3dH8nOiHa9mnI5;>tIXOByIy*Z%JUl'
    '!-Jv}}?K0iM{KtMo2K|w-7LPJACL_|bIMMXwNMn^|SNJvOYNl8jdN=r*iOiWBoO-)WtPESuyP*6}'
    '&QBhJ-Qd3h?R8&+|RaI72R##V7SXfwDSy@_IT3cINTwGjTU0q&YUSD5dU|?WjVPRroVq;@tWMpJz'
    'Wo2e&W@l$-XlQ6@X=!R|YHMq2Y;0_8ZEbFDZf|dIaBy&OadC2Ta&vQYbaZreb#-=jc6WDoczAeud'
    '3kzzdV70&e0+R;eSLm@et&;|fPjF3fq{a8f`fyDgoK2Jg@uNOhKGlTh=_=ZiHVAeii?YjjEszpjg'
    '5|uj*pLzkdTm(k&%*;l9Q8@l$4Z}m6ev3mY0{8n3$NEnVFiJnwy)OoSdAUot>VZo}ZteprD|kp`o'
    'IpqNAguq@<*!rKP5(rl+T;sHmu^si~@}s;jH3tgNi9t*x%EuCK4Ju&}VPv9YqUva_?Zw6wIfwY9d'
    'kwzs#pxVX5vxw*Q!y1To(yu7@<y}iD^zQ4b}z`(%4!NJ19!o$PE#KgqK#l^<P#>dCU$jHda$;ryf'
    '%FD~k%*@Qq&CSlv&d<-!(9qD)(b3Y<($mw^)YR0~)z#M4*4Nk9*x1<F+1c9K+S}XP+}zyV-QC{a-'
    'rwKf;Nall;o;)q;^X7v<mBY#<>lt)=I7_<=;-L_>FMg~>g((4?Ck9A?d|UF?(gsK@bK{Q@$vHV^7'
    'Hfa^z`)g_4W4l_V@Sq`1ttw`T6?#`uqF){QUg={r&#_{{R2~'
)

_HOT = _d(
    '3jhEO000mG01^NI6#xJj000^Q0384TAOHX&001Qb04D$dDgXd2001ul05SjoH2?rN0024w06YKyK'
    'L7wi002Y)07n1-N&o;%002(_08sz{Q~&^1003D409*h7UjP7M003kF0A>IHX#fCh003?P0C4~SbN'
    '~Q$004Oa0DAxcegFW0004sk0EPeni2wkL0052v0FVFxlK=pg005W(0Gj{+o&W%#005%^0Hpu`r~m'
    '+~006B30I&c6vj70K006iE0J;DGy#N5f006=O0L1_R$N&J!007MZ0M7sb(f|O}007qj0NMZm-2ed'
    'J0080u0OSAw=Kuie008U&0Pg?*@&Ewz008#@0Qmp_`~U#|009320RII5{|Es83IP8N0RIpG{}KTI'
    '6#)Mi0RI{Q{~ZAT9{~R%0RJTb|0e+dDggg10RJxl|1tpoGywlM0RK7w|2zQyKLGzh0RKb)|3?7-N'
    'dW&$0RK+_|4{({Q~>{00RLG4|6Bn7UI71L0RLnF|7HOHX#oFg0RL_P|8W5Sa{&K#0RMRa|9b%ceg'
    'OY~0RMvk|AqknhyeeK0RN5v|BwLxlK}sf0RNZ(|C<2+odEx!0RN%@|D^!`r~v<}0ROE3|F8i6vH<'
    '_J0ROiD|GEJGy#W8e0RO@O|HT0R#{mDz0RPMY|IYyb(g6R|0RPtj|Jnfm+yMXI0RQ0t|KtGw=K%l'
    'd0RQX&|L*|*@c{qy0RQ#?|M>v_`~d&{0RR63|NjU7{|o>B5C8uY|Nj^N{~Q1RAOHU%|Nkcc|0@6g'
    'F8}{B|Nl1s|2qHwKL7th|Nln+|4RS=PXGT>|NmD1|62e5UjP4L|NmwG|7rjKZU6sq|NnLW|9Suae'
    'gFS~|Nn*m|B3(qjsO3V|NoW$|C#^)o&W!!|No@_|ET}}tpES8|NpfA|G5AEy#N2e|Nq4Q|H%LU%>'
    'Vz;|Nqqg|JeWk-2eaI|NrCv|L6bz>;M1n|Nry<|M&m@`~Uy{'
)

_JET = _d(
    '004jh0E7Sli2wkN005Ez0G0p%n*acx005)_0H^=}tpEVB006cC0J{JHzW@Nl0077U0L=gZ(EtF}0'
    '07zm0N(%r;{X8Y008X(0Pz3-_5c9-009300RI30{{R6000I911pfdD{{RjD01^KH6#oDj{{S8T03'
    'rVXB>w;@{{Suj05SgnH2(lO{{TJz073r%ME?Lu{{T(@08#${RQ~{3{{UV80Ac?CWd8tZ{{U_O0CE'
    '2SbpHT({{Vge0D=Dih5rDE{{W5u0FnOymHz;l{{Wr;0HOZ?rT+k^{{XH30I~l7wf_LQ{{X%J0Kxw'
    'N#s2`v{{YSZ0MY*d)&Bt5{{Y?o0O9)p<@f^V^akzm3Gwa>_3ID$=M(+p7XRTH|K1$`+aLeeBmdMU'
    '|IsP`&Mg1RF#pFh|HL-`!8!lFJpZ~t|F=W`v_}82N&l@)|Ef^`r&Ir=R{x+{|D9d`nqdEzWB-(9|'
    'B!0`jcxymaQ}yM|ATk`fO`LZegArZ|96A`bBF(MivMkm|7wu`W|aS9m;Ydz|6QH`TA=?{r2kW=|4'
    '^#`O|Ab)vHwQ2|3kO`K)U}tzW+JF|2D+`Gspih%Kt3R|0&V`Ce;5U*Z&{e{~X@`8R7pH<o^@r{}1'
    'c`4DSC4@%#q#_yYL#0Q>O({_Oz&>Hz=d0RQ3u|K0%q+W`O90RPhf|Ih&c%mDw$0RO}Q|G@zNy#W8'
    'Y0ROfC|FQu8t^oh50RN`||Dyo^p8)@y0RNZ(|C9j#kpTaV0RM>q|Aqknf&l-10RMUb|91fYa{&Ku'
    '0RL<N|7ZaJWB~tQ0RLS8|5*V4RRI4|0RK(^|4IP=M*#mr0RKM#|2qKxH~{}N0RJ!m|1ALjDFFW^0'
    'RJKY{~iGU8UX(m0RIyJ`VRp13jpy50PO?-=l}rZ007?r0NMZm)&Ky}007MZ0LTCU!~g)l006rH0J'
    'Z=CvH$?B005`}0Hgo_p8x=x005Q%0FnRzjQ{|N004vl0Du4h'
)

_PLASMA = _d(
    '4G4!22Z$2~i53Tn83v3S28|sCjvxk)A_kBo29YKOkthX{Dg~1)1(YrYl`jRBF$I@11(!7hm^TEOI'
    '0TwH1e!bqn?3}bKLngX1f4?zo<swlMgyNn1D{C)pi2XxOah@!0-{g?qEP~)Qv#z^0;E;}q*wu@Sp'
    'lV60i|34rd|Q2U;(CK0H<RBr(^)9W&o#W0H|pIsA>SHYyhZk0H|*OsBr+OasjAx0jPBWsCNOVcmb'
    '$-0;qcesC@&degmk01gL=or-KEjgaxOD2BwDxricipiV3BQ3Z;z;rH%}wj}4@e4x^F}qm&S$l@Xz'
    'q6QP(CpqUk)niij&7oMFMot_z;pc<T^8=ImXnxh_?r5~B5Aeg5im#89^sw0)FB$TWsl&vR|t|*eQ'
    'DUq=%kg_X}vn-CZE{(M>jJ7a~w=s&iGKsn~h`Th1yfuftH-^4Ag}*t3z&eA$JA%SIfx|t3#6Ew;K'
    'z_zSeaAw4$U}R{M0(0addo(6%tv_4Nq5akcFs$6&rEdCO>@ysa?($6(@}BMQgGE%Z`D+8)>UoSR&'
    '3Z;YuQ+8+FEMbTWQ-|Xxv?A-CkziUuE85WZz<A;A3OqWMblFVd7?B<7i*xX<p@OUFB<C=4@Q&Zd>'
    'PXTIg_D>2X-;a#!kfSL=0F>vmP_cU0|pQ|)?E?t4-1d{OUyQ1E|G@PJP7flcv)O!9<F^My<Ehf4H'
    '_N%V<G^@~UKj7Ij2MfQ(G_mD*Qkwf>BLim(H_?1BUmp}QKKKYtH`kOuaoILuTJNutH`=L4eqB#7c'
    'IQ*qI{H8Yis5ShlH2teH{j4+nt}^|vG5xVH{jx9pv@iX&F8;SI{<tjux-9;?EB?JI{=O>yz$yL0D'
    'gDDJ{lzE!#wY#AC;iGM{mUl&%_aQKCH&AO{L&@+(<J-VB>UGS`q(7;+9dhhB>CMX_}?Y?;U)LtCH'
    'Led_U0z`=qB~)CiUwl^zA3}?kDr`C-U+q@$@F~^(FB4B=Gqm'
)

_INFERNO = _d(
    '000C500jX71_1#G0s#sF0t^BI4g&%Z1OpNT0~7@W7X}0w2L&4l1sw?n9|{K|3kM_&2qp~(DGmuM5'
    'D6_23NR81G879m6$>{O3pp4JJQ)l=8w^1l3_~6aMIQ`EAq+|*3``^pPbLgeC<{|53sox%S1k)!FA'
    '7^R3S2S@UNj0{HVI)k31T@3V>=0CJqcw#31&bFXF>{SL<(p{3Ta0RYDo)fN(^gE3~NmdY)=hrQ4V'
    'ZU4sBEqZB-9#R}gMl5N=u#Zd?*>T@r3z6K-J>ZekQ}WEE~@6>eu1ZfO>7Y8P&77;bGCZf_ZGaT#u'
    'M8g6tNZgm@OcN}ea9Bq0XZG0VVeI9Lp9&CUgY=R(cgdl5$A!~;rYltFhiXv)^BWaBzX^$jnkR@o6'
    'C1{f-XO$*rmnUYJCuW)`Wt%Bvohf9WDr2B3W1=f!qby;iEMTTBV5lx%sV-itFJ7%MU9K=(urXV)G'
    'Fr1TTC_7+wlr9`HCMScR=PG-yf;+6I8(nlQouS<!8%aGJ5R(sPR2b=$39HRKTFC$O3Oh>%tA=cLr'
    '2d<M$kn?(ndtnM?=&|Le)w^*GoUxOg`C7J=#t@+fX~*Q99mIINwt@;8ix^RyE>RG~-z_<XSQ1Trl'
    'QcFXvt^=wL1BVJqrmD(hq^>t-nIXD01wCGKh@?`$LQZXxh*An|b@@pB#WbR6?`8}oP>^m!Qddl&V'
    '67507<_J9-jf)e+H5cq`;_=gVoi46IR3;B!+`Hl(tkO=yc2l|u;`<4d#mj?Tp2K$=^`<(~;p9lP*'
    '2>hc7{G|%~rVRY34g9JP{HziDt`hvP6#TLl{InSRwi^4m9s9Z;`@A9hz9ag;Ci=oC`ot>w#x42BF'
    'Zszb`O7u<%{TbZI``2%_tQZ3)kF5zM)lcA_1jGJ-B0x2Q}p3h^W$3c<z4dTVe;r@^6F{v>}~Pwaq'
    ';hU@$q@`@_q93g7fu;^Y)7L_>T4YlJ@$R`1_jq{GIy!q5S`('
)

_TERRAIN = _d(
    'Gc%boHk>dxo-aG0E<U6zK&C50sVYXSC`hg+OR*+Sv?NfrBU8B|R=glsz8_n`9$v&8V8$C`$r@(N7'
    '--HHYta^N)D&>m6LZ-TcH9tn-Vb}>4u0eefaVK>=?aGI2#D?ni}41I^aPOh1C#jzmiz#i{s5c%0G'
    '#yzp6>vm=>VhS0Hxgkrq=+e(EzK<0IkIUufG7Xxd5}X0JW_Ewx<BOp#Zy^0KJs}zmEXHi2%cc0L6'
    'U($9Dk9aRAF}0nBCv&1VVDXbsP45zlEA&}tdcYaP;TA=7Oo(`_l#ZY|YsG1hQ3*Ks-5aXr{_LD_R'
    'f+H^_VbxqrKQQUS_-FI2ucwOIlVc&UW;CgA{du`%;apQe;<9&JLetqSCf#!gP=YfgmfsN>bk?Dh#'
    '>V%o=g`Mk#q3njG?T4xEh^_C5vG0ks@QS(di@oxU!Sjv9^Nq>$j?MLt(e{wl_mSE6k=^)`;rWy0`'
    'jqMWmF@eL@%)zc{g?UvnEn5m{{EQ!`<MFpmiYFS_VbkV@sslIlJM-2?&*;1=a1^-j_Bfz=HH9t+='
    '}AbiQw0W-qnZP(uUg5h1ku6*2{y`$b!<vfzZQ%&cJ`nzJ1EOe8{<b#<qIIvw6a?c)+fAzN~h<sdc'
    ')ibhxB*wxV*hpK-FBZ?Kwfu9t1Bm29e#Yp9TFrj2Q&i)f;VXP|{<o`YqafMl9}VwihjmU&>5c3+Z'
    'nUXXEJj&59xY+H(HT8L*^hGbZTVpoD+R)AbofnHXFU|EG@T!&>|iD+SqYh;aWW{+@bk#cO4b#9e+'
    'ahG~@nS6Gee|epPe4m7Vp@)H^iG-z$hNq5+sgaDUla8&Hk*}GQv745&o|(0voVTN&xuv1IsHDBCr'
    '@yVK!LY2uvaiLpvB$Tx$-1}8yt&Q4ywAeF(Zs>i$Hdji$Jfls+0M+{(a+t}(cjk8;n~;Y+u7yb+~'
    '?rm>Eq(-<>c+?=kM$4@$KyM@bC5V^7r-h`S<tx`uhF+{Qv*|'
)

_CIVIDIS = _d(
    '03uERBToP%Q2-@V03}oaCRP9^SO6$l04Q4kDO~_6UjQm$04rhuEMx#IW&kZ{04{0(E^GiVZ2&ND0'
    '5EU>F>nAeaRD-M1v7C7GjI$va1S+b5;brXHgFa<a2Pjl8aQtpId2|1Zy-8vAv<m(JZ>aBZYDi$Cq'
    '8Z|KW-{NZ7V=+EkSKAL2WNWZ81Y_GDB@ML~S%hY&At}Hb!hXM{GGrY&uA6J4tLjN^Ct!Y(7hDKTK'
    '>uOl(0-Y(h?KLr!c&Pi#d{Y(`ORM^S7@Qfx_6Y)VsXOH^!3RcuXFY))2ePgiVES8P#OZBkinQ(A3'
    'QT5VNZZB<-tR$OgYU2RxiZCPG!T3>EkU~XJtZe3w+USe)uV{cz$Z(w9^VP$V(Wp86<aAaq2WoU3^'
    'XmDm}aA#_9Xlik3YjJ99acgaIY;AIEZgOpJa&B*PZ*X&PadUBUbaHZZa&vTZbaixeb#--hc6N4mc'
    'XoGocX)Vrd3kqwdU$(!czk<!eSCO+e0Y9+cz=F)fPZ*_e|Um`d4qv@go1g6f_a96d545}h=q8Gg?'
    'NgFc#DU4jEH!Rh<J{Pc#n#Bkc)Vci+GZZc#@5Hla6?lj(3%hcb1TMmyvgvl6RSscbb!So0N8(m3E'
    'z#cAl1YpO<x@n029<b)uPdqndQ2n{=g|bf%nir=4@Co^z?6bE=?otDthMp>nOFa;~FsucUFXrE#&'
    'PaI>axw5M;isBgBZZ?~y#xT<cst8KchZM&^)ysm7$u57-qYrn8-z_Dt<vTDM!X~VN=#I$I|wP?n+'
    'XUDf^$hc<7xn;|_Wz4!{&AVgHykpP3V$i-~(Z6BRz+ltBU(~^0)xuuZ!(G?JT-n83+QwVk$6DOTS'
    '>4E3-pN?s%2(jaR^iN5;>}d#&Qs;jQs&T6=h0B;(ogBrPU_Q4>(oo_)k^NxN$=N4@YqK2*+uf&MD'
    'yE1_1r=B-9Pu<KKS1}`QSSH;W+%_HvQu?{^T_N<u(51HvZ^1'
)

_MAGMA = _d(
    '000C500jX71_1#G0s#pE0t*5H4FdxY0|OES1QZ1X76t_v1_c@i1{??n9tj5^3J4+#2_y^&CJhQH4'
    'ht&~3oQ{0FA@zg6Ad&J4mK4II2I2(7!N%e5I-6aLL3l89T7(!5lJ8sOCb?XA`ws|5>q7-RVNZyDG'
    '^#K5nL=0Uo8<~FA-xg5oI$FXEYFLHV|t#5NtUQZaWWfJr8j|4{|^cbV3hxL=SdF5O+rqcu5d=N)U'
    'NW5qeG$druO3Q4)Mo6MR$?eO45GR~3F)6@FS4eq0uRT^D~}7=K_GfMOYdWEy~F8h~dTfM^_nY8-)'
    'U9f55ffo>jwa36tkAAxfqfpsB)b|HayB7u1#f_o!^d?SK>B!Yk?f`KK0gC>E5CV_@0frux8i70`K'
    'DS?bBfsQJHkSc+ZD}j?MfRrqNmMnmnEr6LVfSWFVoGyQ!FMpsff1xmbqcDD@F@B~oeW)^hsxy77G'
    'kmQye6BQmur+(KHG8u*dbKusw>NpXH+i}^c)U4yy*YQkI(NW2cEUS##5{GyJaorBbI3k(%06<;KX'
    'J`KanC?-&_Qp~LT}SUZq-C>)<taCMQqtdYuiU^+(>EONoe0nXy8m|;!S4bPG#gzWaUs~=Tc+nQ)1'
    '~<V(M05>sMgxSYYj1U+!C8?_FN-UtaNGUGidG@?>1|WnA=UT=Z#N^=n-AY+UwkT=#HX_i|kLbX@p'
    '$T={ri`FUOWdtLf{UiyDt`hj2jgJ1iFVEcz*{E1=wiemhXWBiU}{E%h+l4kvsXZ@CF{g`R}nri)<'
    'YyO>V{-16Bp>F=8Z~mom{-<*OsdN6SbpEV%{;qfauz3Emdj7O~{<eJnw|@S)fBw6H{=I_!zl8q5h'
    '5o{a{=|s>#)|&PjQ+}v{>+d5&5-`jlK#<@{?nEI)tCO)nf}<C{o0)U+@Ag3p#9*X{o<qj<E8!Or~'
    'T)t{pqUx>#Y3juKez>{P42;^0fT)w*2<E{P(&1`Mdo4z5M;Z'
)

_COPPER = _d(
    '000010RRF50R#d81p@*G1Of*I0|^BK3I+rV2LucV1r7-X4+#bk3I-7i2NMhj6buLz4G0zv2^S9u8'
    '4wB@5DFU+3mg&)9uo{76bv8~4Ivc`BNh%M7Y-#C4<;B7C>anb8W1WQ5i1)JEF2Op9TG1d6EGeVF&'
    '`8&AQUtq6*VFiHX;@{BNjO%7dj;uJ0%!BCKx^^89yi)Kq(qQDH=m68$>G`MJyafEgVQK9Z4=7N-r'
    'KuFdj`XA5JkJPck4-GaynlAyYIVR5c=1HX>FxBUm>hSvVwGIV4*;C0#ouUOOgVJSJd0Ct^M)V?HQ'
    'kKPY8DDQ7_`XhJG!LMm!QD{Dk6ZAC0@Ml5eeEpSIIa!4+7NiK9rFLg>UcS|sMOfY#(F?vlgd`>cb'
    'PcnW`Gk;JsfKfDpQZ$28HH1_(g;X|&RW^uLH;Gp_idQ&{SU8PYIgVO6k6SvCTRM_lJCj{IlwLfQU'
    'p$vzJ(yrUnPEPfVm_Q=Kb>Pgo@79uWk8{3L84|sqh~^-XhNoGL#Js&sA@#1YecGSMXYT_t!+lGZb'
    'q+fN3n26vT#VVaY(dsNw#xIw{%LlbV|8(OS^VUymw5!cuc-{O}}|f!Fo=@drrf9PsDsr#(hx7eo)'
    'ANQOSQ%%YahMfl|$aQ_g}@(1TRbgjCXnRnvx5)P`2phgR2!SJ;VH*@;-&idfu>S>23T-i=z|jauQ'
    '3TjGyf<B(kCkzD4HUFVWr=#yUQlwRwUU+k4%?UrEfmtgRiVeyz@@|j}unqu{vWA>Y4_nc(-on-o+'
    'Wc#0G{GVn0pl1G|X8)pR|DtFAqiFx6X#b^Y|E6jGrfUDEYX7Kf|EX*Ls%-zNZ2zlm|Ez8Qt#1FVZ'
    'vU=t|F3WVuyFseaR0G!|FUuavvU8ma{sh*|Fv`fwsilubpN<@|G0Jkxpx1$cK^F~|GRhpym<e;c>'
    'lh6|G#<vzk2_`djG+D|H6C!!+ih4eE-CK|HXa(#(w|Ce*edR'
)

_AFMHOT = _d(
    '00002000C400sa62mk;I000aC01f~E5C8xY000yK02TlM7ytko000~S03HAUAOHX&001Na044wcC'
    ';$K|001li04@LkFaQ8D001-q05$*sH~;`T002Ay06qW!KmY(j002Y)07d`+NB{sz002w?08Rh^Py'
    'hf@002|~09F71SO5T8003M70A2t9U;qGO003kF0A>IHXaE3e003+N0B!&PZ~y>u0049V0CoTXcmM'
    '!;004Xd0Db@ffB*o30sw>r0EPzuhzJ0R3IL1^0FDm;kPrZp5&)DG0G1a3m>2+>8UUOf0G=NJpdkR'
    'FA^@Z$0H!AZs3`!dDgdl40In|purUC#G61wR0Jb*(xH$m2Ism*q0KPu}z(D}QLIA`>0LDiE$VmXo'
    'N&w7F0M1VU&`|)=QUKIc0M=Ik*jWJDS^(T#0N!5!;9&sbVgTf10On@^=xG4zY5?qQ0Pb%9@Noe0a'
    'sc#n0QPqP_;~>OdI0==0RDdf|A7Jjg9HDB1^<Qz|A-0yiwpma4gZf1|B(^@lN0}x75|nO|Ct&8n;'
    'ZX~9si#n|DhrOqa**MCI6-;|EMYdt1JJlE&s1C|FJRuvors+HUG9Z|G7E;yF35AJ^#Ny|G`23!$b'
    'eXMgPV}|Hw)I%S->wP5;kN|ItzZ(^LP{RsYsk|Jhmp+gtzLUH{)-|KVZ(<75BiW&h@9|LAG|>udk'
    '*ZU66Y|M7AE^K<|7b^rEv|M_|U`+NWWegFS||Nnvi|AYVkh5!GD|Nn{q|BL_sjsO3T|NoKy|C9g!'
    'mH+>j|Noi)|C|5+o&W!z|No)?|D*r^rT_n@|Np7~|EvH1t^fb8|NpW7|Fi%9wg3OO|NpuF|GWSHz'
    '5oBe|Np`N|HJ?P#sB}u|NqJV|I7dX&Hw+;|Nqhd|I`2f)&Kw3|Nq(l|J(on-T(jJ|Nr6t|KtDv<^'
    'TWZ|NrU#|Lgz%?f?Jp|Nrs-|MUO<_5c6(|Nr^_|NH;{{r~^}'
)


COLORMAP_LUTS: dict[str, np.ndarray] = {
    "viridis": _VIRIDIS,
    "gray": _GRAY,
    "hot": _HOT,
    "jet": _JET,
    "plasma": _PLASMA,
    "inferno": _INFERNO,
    "terrain": _TERRAIN,
    "cividis": _CIVIDIS,
    "magma": _MAGMA,
    "copper": _COPPER,
    "afmhot": _AFMHOT,
}


def get_colormap_lut(name: str) -> np.ndarray:
    """Return a (256, 3) uint8 LUT for the named colormap."""
    return COLORMAP_LUTS[name]

