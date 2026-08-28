from __future__ import annotations

import base64
import copy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import zlib

import pytest

from acfqp import (
    construction_k7_standard_2048_formal_transport_recovery_v42r3r4
    as recovery,
)
from acfqp import (
    construction_k7_standard_2048_formal_transport_successor_v42r3
    as retained,
)
from acfqp.phase3e_ids import canonical_json_bytes


_FROZEN_ROOT = Path(
    "/home/erzhu419/mine_code/"
    ".acfqp-v42-local-formal-transport-ordinal2-v42r3r3"
)
_RETAINED_FILENAMES = (
    "FORMAL_TRANSPORT_PLAN.json",
    "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json",
    "FORMAL_LAUNCH_NETWORK_START.json",
    "FORMAL_LAUNCH_OPERATION_OUTCOME.json",
)

# A compressed byte-for-byte copy of the four small authority documents needed
# to verify the retained occurrence.  Tests therefore remain hermetic when the
# production frozen root is unavailable; a separate golden test compares these
# bytes to that root whenever it is present.
_RETAINED_GOLDEN_B85 = (
    'c-rk;YjfMix&ANu99et6^iy>bweiH3JhIxfQ+F_Xl^Bx*OOSTdj{p04761wGB3X9gBt0jN9g768yYKyZ-d*@VCx5'
    '!SetG_)dU5`j%dfw!E-!Arzq<aedVO<#ee>*xrk<bt;p9JWPTXphW{XudiEmE+@a81Nz(h*cSedAyN~;)RlGcSpm'
    '9#=BM~F)#>EyhOE<_QGV!=v5NecSS$yaYqLOowC>*+KtE4N<V)yv7hQ&ZLR>3#b-%~zA)Rw-7Kd9z4iHL2&7%PZW'
    'zSo>+YhHtQ()pDJ7hilv{RVimYRK-cNaI0`vEz@G^?yFoc{UpXTdJ<pF+!V5vDOdNcgiyfcH|N*iRE!8y{ptGR^|'
    '#f{#r4bQmr&MU1*@(vUS8c?R9DyEv|q7Sq<*A%TD`BAZ>whImRp^%z$v9d2O&)Io>-oxQY4X(yu=q#o9G!A-cn+0'
    'AX+EmeHK9|?z1=J306x7ozxf{GR-$LNaIx|PQ)l8)UBDc6qdn2S<1wW&dC@Sw8SKy$sAKMF$K#ltS2aKXSki#9y6'
    'pLQ&_huua|K$cT>#3aCswIuiY6mdgtDyPSg|!rPhnI+*s(%N#|be1g-I!JJ_|xECJf8Gt5@MuV!^j6%m9~ZXT=L+'
    '|L8<@(Dtx!A0WMq{C!QxJxtF&g4S=*W%ebSm;1k%{qkCH1%@VK;`BoZ`an1Q@u;eX0vj^p7Ceo&B=$8ul8c)>ea>'
    'd`OWjI%j)VcH(y`9y!fre%QCsxeSZ)+Gq-%3mY*CnuGpuwZg$h=i^R;<U#fb&3N_ZU@oGXHCnmTcH8YF`t1?&kNH'
    'is$WSy0DnYkEAR*@=YybU=Tj$hI1{M(9~E+uqks20oAKz~mNnvG7v)HO|e@zvGqo9gBH^>-K7)%VYDzJ(7~7k@kd'
    '`UYD5`r`SkoA$Y73TXmA%r2B^=IiP7Gs5M-HlG_ZH`nKvuU}nV-&E%}Hy1BojZ4g@=I`F4H;Uc&>|UI~9+07Y_hr'
    '3!>eh3tbx`77B2WfioPvv<vX~Tc%EXX)&N^_fsYN2NHmG1M*M^xuMdUF?iM+uSKKwSEd0K}-)-RFj_NvTKTsDS#x'
    'Vpei9LmMU@%vS2p}c}7HBUlvDpjyrSd>+y4?_vG5WNeO8=)y>6ops@Cwy5qCp7Dkt3N$#9&(1KMNhd}ua^NqU(aT'
    'fReRA2My*af7-^Jb#3(?D7`U@e&@7k~5WprrethQUlbo8ZE{vweNG23ikSU?asKIM5vSup6Bwmvwm`gGuiCW{BO-'
    'c$4qb4J`*jd_YnNo*tBD1*a0%OtU$S94*L5oJf8=y;SIN@4~?&13eiinkqvq@6~f7sB2^7h4WMiS`+Cy*j&8azvZ'
    'mn91ks5FcOue^hY!TG6-6bQ?5qI9q@wPdbc$$CCnRdb}9!K$aNb(Z{enP&AWo%XKJPJgOrKWozR-6W))#5iQcS1-'
    ';lcMwE9n}q7FhQw)6!;cVkZz~s;b<-d+k^AN)L_5WyE=+b)+dd>HvQ)j*e7&AWx4Z|ox&=h&GwHO(hYHASI)$g=q'
    'l*tfg-?X*p9wnlGyP-39QSlBfhK7}-jmcNlV!3ZAQQ4AmCr!olqC*7S2QQil}A`Hcu1rU{;z$P3)7E9nn8!fB3qA'
    '1%YWak1+}NI*T_hxuVLY`#P+e?LS3?iXWu3O+oo9~19Y)otQ=PB;p!;g`r<4FBQM*m(d<UW5IB<t>0urx<*9<A=G'
    'ETBlli;4V2z9-H|=U%ufKLJm}2|D=GJZ*Fm7udf4^$&4E^S1J*%4Jrg&<WW;s4#u*t|rdi>ty#WE2L_>={;I0@>2'
    'r!H@C%Y4<e6akJ>H<MKjPhQsb>Iox3(SDj*gxn3$+&Lyyh2?~|4FaQHHAp#&rwp}TET$8z$*1|`7J;*hle%i~BW_'
    'wwCrH^<cpuwY)-%_%*l(5gMqWH<ZYaJAZnkh3ab)`K5}}LLq{nseq+%wx!n%c%lyOB%9mg6xYI#*}&;cV-IsoOAo'
    'eMq|xFL|=P2k1{r5$xKNYd52@^s;3?UR%cCB*jo+W$~uc6Gn#E|*z)#5qM_1|vi)-?f*TutX(p&W4qLq;9qe_}Sv'
    'Vs}-$*y5gro;K6gI3^J~DGLxL5OM-BdodA>8$`gTGwBS5ID672H+&Ly}&R_x`e#x})c>HfB6V3-~i6a3;f|w+nLr'
    'DRHNw!pC;xV%T8st{EoCHdoB!Oosq~=i@KSqQ<1CIR&@+)Ch)$iveid(tb5U%{P4T;WmJEkyjn~mo_4L*HLZ%+qL'
    '<w=TA|JQo5EXl0PTch}yk5bXny@wx^>a+2NK2SgW(ze`A)--oWHn&)Nb67W?QUJyS97+F=4AGam62jHIo=@f&F{f'
    'pkhxBM>?B<F!)IEozz__>RpgGY3^X5~=K@yteAse>IzNvr}Z_}!3AzWSH!5n5;9?i1HM&DMs^dpk!-YPrr(<1NUC'
    'iT+<AL>*o26NQQQb5}>vx=b3T`fHvXkHfsg!K{{2Agy3U+<Tbu2^Ap5U&MANRWdTiglo*^%B!pN8#R>CH<tL^AVr'
    'iaz7$9v6@irnGnV2vj-jZ!Kp;JCnP9BWp>6mXPgCyPE0y4fZ_#JPX7wIY+DWDAlIW=Y?J{J8CxTbtkPQVXHA92wf'
    '^)>*xW^|YqpE<TdxF$ST6u+>$e44rD4id@W&G1FJb@5kAnyIu<p&t*<C$LXB)VEHk-@~+KK7x*_O2J6SmQ4eWCv;'
    'qn&kQj9s*cw5$6^p_rmd*kf1>IKpV@nek8$*lVJWGM1u}+6j-E;Cv*2Xg@0!TZXe%#4|WP%HX==X>WD$g~ADA7h<'
    '1*&QeT)7^i}X)~oEfc2?%n#|lyj$t=@g$CA<{lI9E?SqG_uu?~fj1ks_he&P}BT`X&#c3NCi2*#t4F$bqXx;0fyQ'
    'bBbJ9v<Z+Dl7gNAV9!A1B50F%`SRj1(j?EGL0tMYZ<v995>8!X;|ih7!hLjz<JqH?jaS%&83^9bh6q-%0lTYVX{n'
    'R)b3|aX8lM@c-5pd#~Z|9Op7!xLsxZfLvsq`QZ65~L4Uno;Yh)8Imw{;Y1MZJ)=gngn_dLSCiv9+c3AtNZMLL&@~'
    '%s*ed}PeO|j*eW3G&3w^3f|6Tz)3g@1tzHr}#23IRHviP@1{`;ysB{oXahPRpkZ(x<lBdQ%>bG^Rg3%BF`_OdjsT'
    '^dkepPpVa2rFlG<-$AIt?hkuNqlY%rJ>jX}L-_F!9#ZKK@Wy#ZC}0q`>J-(^aQ;89FD`GM5?~wL>yZz-@Ii=xjm^'
    '`vB|95sSW3AyhMW>f@~NOioEjU`slqQT$VTb9J?0XGZF8mon^Ac5-*0Ql**mv9n@;>$?;B^`4coHXHCUT8K=U4KR'
    'kzD}z39d$*Pk`hNl5LFrzmY?^!bn7=S|~uf56g<>CORcq|Dj7V55OpTAm6==_%?<I91VkqhnxMv%_&_4!CI14#6;'
    'CDMVXz+-KZQuea?zWl?>8dO{~~agVGt2b<|Zeb-V8T`})<+ut+Dv(e7-40b*1F7xqllct`w$stc&F*+SC%}W~!(;'
    'QwwzM2m9+Z+8EW#b73F!>Mu6=h%Xe-^Ec<u5ASk-aP7eSTThuyg@MO{cmve|H2P2}3mdYNOaPYL9ZjlgnBT7TXT9'
    'i#z};GLi&>nq{vga!HV=Xo-8}LQIyY=#$Bg8IprR4YM);X{pE)xOmEayP%rGf#3ED>jZ5*q0`5awHv~SW#&^>zo+'
    'Vv5I~8%>>1dcT#7-O%me-pv=kYWTE`5m9EkOlFvBcY)F5m#$t)>KsriTyU5tj+^cX~ygmNN2MUK&Mdnk}Z9!au7i'
    '0G(iUYejSD_st(+bf%iupZ)+Jt6HmFk>V(8)PR9IsKEwXoK>IAj)vdK3$A>+77oXNc6#Y<V$BjWF%4wKoN^c69tT'
    '$Dba*cA5;LIB~cqCg66rnQ!4vtJ(qbvkS<DkEHc6rok*cgj{`GZmH_$(zF(}nb07-@-m3jE&eE*?;ck7KR?|*<le'
    '+y2m+EDQ(r1$<bfG<oO~(vkp`Rt9``Knig;kzRQ>T-GO>{SO{<?GXqMpoqI)!J>a&s2?#J+#$z`J@*ww=YjbCYRH'
    'pf{}%Nwh|FrYP2CE5)(<$}X-{+Q`=A{e4~A-2s?1-PXcC28E8z|A|GXAAQrI*{p#oVio6lyn>ngaeKW#ZZW#DrEo'
    '9L|5mc)r>*YMwGa+{zyXCIUuHEQpS^58EAw;C{@9#{BR*lS>#M7q>YIxf7k@s#x%j5~>+_56tIMnE#nsn<X)l4=u'
    'K!;B>G_L`*I3a%hcQ<53J`4Tdx8kg8Nu(O>*l>%RC$>O=QPq-i<D~B=JM_U!}SlJajxJH@ILW8&R0JT7`~m?@8|9'
    '8&B#PgXr;7m^V3eE)2&3q&U(M&e)j75<t2>r-R0Hym({mduWw#=fHd8@a6baTU-Do>*W%wG^H1s+JyFcjG`okFN~'
    '18OSX$Dq9IP33OgE=mhC?NV?H`_loOkV>5kcNz1)oTqhr0*gYY(7J@?;lvC(kppfGMTHBa(``z!Jl?P$oL*GELTm'
    'Y(1wsm~zx6aDxA2mWt%Q#dUPPJZVokyesqzCNDjYA2+iGFg4|4bQpq`6EWa>Ft3+jeKHa4L<VWJ&RReZ>IHst6-B'
    'a4L{B7rc-D5~17z$SNKlz}k5@)#QQ?7TBnO-fF8C0Q)zKs$r8bl&FM@Q5ghD=9(wU@?;bvT+Y7zhN#KY0eF<TZ;o'
    'g^4h$_RmJq*iKCPRcTw6p4xe^#Xn*sM}fREeT3NBPszC`yie&Uo&@$=5ELeKxNtmBgzhF!Bqv=L=ugFgE|chCI=>'
    '7FlaK-#7vcDg~lsFLDSPCCVe1!Ga<Yj<>8ST)G%$0)|w{J^h`4+9ulbxb!V3`4@f)r1}xnP#T+qxiu%mM8vi{#=P'
    '$o4(r4R|>5j(WVc(~JFxH_xqS4(^QrBpx!QaNMv{26$)3kGZ{Aq)Iypgu49YZJUpo8UNy;vQ4Xd4pSJk;FJS9ht|'
    'OO%`2M|&fCo2I2*yWK<C*~{IC+m?eF2>o*6rjvj7E8IO=X*JSIL^4oH`y9Ch!BqeeB?6R67JP~#LwK(kEq&aOf)3'
    'JpC%B^_ckQhGIq+%L%C<TDz?>kQg6>4lB{NZ_D3ddeXqBa8A$W%Yc?4fA8`~BHRmqH8D?QP^E20n9q3z2M$YD$;k'
    'fy+RQh1t%1SzaH4jG(l)NkP>0UdT0Bv|HX39+1WLKz71c$Q5_4DH?0DBYy+ANpqVBm3kVqYZmr!{GC7TeKZ*8vz@'
    'C9o=25)o%xN50-oIlb=k-8$?_A%RZTxNZ7RWD4flfJ6+U~8JIs6o-zi5x(wn;63IR>=E41eXJDO9{-H(H1;S2qYX'
    '9OBGvWSY>&M1C(g5m?;EoJm+V3CfyYD`*VU9iV`+O?br1p5jDF;jA;#m{w#iJaCG4Y$>a;&t2loiDM8eFc-E(E7s'
    '{h#7;yMFdaXMq?dCAZRuhn{+r5AHs(4VrNu@w0lu)zH^EyjI#w{gIefImes2qX&95N=lDj9`~(|TrIC^ZCgaI|Ni'
    'pD^ULoZnCQVS=mYn!52XCkt?tde)dTI_{o4-gu)VU|Z``|hM5V*E9fe+B{P{00&aYeVJ-X1JyK%ff{(%h+cLP2gc'
    '=|TY<A?QhsC7UMo+T{MFa>s$G|GI`);UQT&<tY^D8;GlrB@Q=UrGQNuy*C7iq36{N=!Y07#EA9bhN}TH=e~1bdEX'
    'O49;T8k$fl1;gpy)1(jjmN`b!uwTfycOkzF+@WaPuJi?e($RJxz%D779<VFr4pI|RK8Dj&KPD129(L{uDF;OEJ)0'
    'A<*Gwmc7pfyS9crf(=CLESBrikE2HW*_Zgj7;FaBu~>rZKQGh;b!tGO#&#BP+ssP*foRvuIGoBnR_u!1X>{-1ejP'
    'fg_EAgDz5-T1jm)=5c`}pFkIthH)k69m^p^Pr2shbsXnS1Zm_f;_m*$%F$W(fUqf^&IQTkML$$*W0J5Q>DuI+XaH'
    'S|fr3Ipa?nYDX2<X?l{6{Nh0)`w`cs6M%XKf-{ji!+N^Tcx_E|6eJP3XN-@o<qC12(F@Qaa--!ACh924nVd!->A>'
    ')8>a-W|u-94dME=o%u$uwy6J4B-UX2IfZXVW5MiBrjnobmue81k8p>8o$I_1SR}Fa#pRE?7@R-@X%0tOU7~HY)Tr'
    'AMtG3PGQ<eeNXk(oiDu<P;*2RPkx{t8XVfX#d0VH%?QxvPP5@HH$x%H93XaDpcOdC-NmTG`gk+g0D&cnUN0C`J`d'
    '8B9R=9^Wi4gP@wa(fSt${1y3dUeaw-74%7(G;)qz;_KBpp>AskL;4iH8w(&kKB3%YFYHy@Tfaxaa=FjQ{)jh2PIF'
    '{C<AnqvscfbMOed@(*=vUY6)y2|6r0pNgaky#4)E>9Wt~kdfv)r}xWg{wJT{|Ak(o-t^Pw>0P^*S+_63bf+l#FAx'
    '5enE%e>fhQmS7tr$z6#'
)


def _embedded_retained_raw() -> dict[str, bytes]:
    compressed = base64.b85decode(_RETAINED_GOLDEN_B85.encode("ascii"))
    values = json.loads(zlib.decompress(compressed))
    return {name: values[name].encode("utf-8") for name in _RETAINED_FILENAMES}


def _source_fact(relative: str, index: int) -> dict[str, object]:
    return {
        "relative_path": relative,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": format(index + 1, "040x"),
        "byte_count": index + 1,
        "sha256": format(index + 1, "064x"),
    }


@lru_cache(maxsize=1)
def _manifest() -> dict[str, object]:
    return recovery.build_recovery_controller_source_manifest_v42r3r4(
        source_commit="a" * 40,
        source_tree="b" * 40,
        source_facts=[
            _source_fact(relative, index)
            for index, relative in enumerate(
                sorted(recovery.RECOVERY_CONTROLLER_REQUIRED_PATHS)
            )
        ],
    )


@lru_cache(maxsize=1)
def _occurrence() -> dict[str, object]:
    if not _FROZEN_ROOT.is_dir():
        pytest.skip("complete production retained occurrence is not mounted")
    parent = _FROZEN_ROOT.parent
    return recovery.build_retained_launch_occurrence_v42r3r4(
        root_identity_raw=(
            parent / ("." + _FROZEN_ROOT.name + ".ROOT_IDENTITY.json")
        ).read_bytes(),
        retained_controller_source_manifest=(
            _FROZEN_ROOT / "CONTROLLER_SOURCE_MANIFEST.json"
        ).read_bytes(),
        formal_transport_plan=(
            _FROZEN_ROOT / "FORMAL_TRANSPORT_PLAN.json"
        ).read_bytes(),
        prepare_receipt=(
            _FROZEN_ROOT / "FORMAL_PREPARE_RECEIPT.json"
        ).read_bytes(),
        local_launch_attempt=(
            _FROZEN_ROOT / "LOCAL_LAUNCH_ATTEMPT.json"
        ).read_bytes(),
        formal_launch_transport_attempt=(
            _FROZEN_ROOT / "FORMAL_LAUNCH_TRANSPORT_ATTEMPT.json"
        ).read_bytes(),
        inner_network_start=(
            _FROZEN_ROOT / "FORMAL_LAUNCH_NETWORK_START.json"
        ).read_bytes(),
        parent_network_start=Path(
            recovery.RETAINED_PARENT_NETWORK_START_PATH
        ).read_bytes(),
        operation_outcome=(
            _FROZEN_ROOT / "FORMAL_LAUNCH_OPERATION_OUTCOME.json"
        ).read_bytes(),
    )


@lru_cache(maxsize=1)
def _plan() -> dict[str, object]:
    return recovery.build_recovery_plan_v42r3r4(
        recovery_controller_source_manifest=_manifest(),
        retained_launch_occurrence=_occurrence(),
    )


@lru_cache(maxsize=1)
def _attempt() -> dict[str, object]:
    return recovery.build_recovery_inspection_attempt_v42r3r4(
        recovery_plan=_plan()
    )


@lru_cache(maxsize=1)
def _absent_remote_inspection() -> dict[str, object]:
    plan = _plan()
    old_plan = plan["retained_launch_occurrence"]["formal_transport_plan"]
    unit_name = plan["retained_systemd_unit_name"]
    empty_properties = {
        "Result": "",
        "InvocationID": "",
        "ControlGroup": "",
        "Type": "",
        "Restart": "",
        "RemainAfterExit": "",
        "SuccessExitStatus": "",
        "UMask": "",
        "KillMode": "",
        "TimeoutStopUSec": "",
        "RuntimeMaxUSec": "",
        "StandardInput": "",
        "StandardOutput": "",
        "StandardError": "",
        "WorkingDirectory": "",
        "Slice": "",
        "FragmentPath": "",
        "Environment": "",
    }
    return recovery.build_remote_read_only_inspection_v42r3r4(
        recovery_plan=plan,
        recovery_inspection_attempt=_attempt(),
        observed_remote_hostname=recovery.RECOVERY_EXPECTED_REMOTE_HOSTNAME,
        observed_remote_uid=retained.authority.REMOTE_UID,
        observed_remote_gid=retained.authority.REMOTE_GID,
        manager_binding=old_plan["host_epoch_receipt"]["manager_binding"],
        unit_observation={
            "Id": unit_name,
            "LoadState": "not-found",
            "ActiveState": "inactive",
            "SubState": "dead",
            "MainPID": 0,
            "LiveMainPIDArgv": [],
            "LiveMainPIDArgvSource": "ABSENT_UNIT",
            "ExecStartPropertyState": (
                recovery.EXEC_START_PROPERTY_OMITTED_ONLY_FOR_NOT_FOUND_UNIT
            ),
            **empty_properties,
        },
        retained_remote_journal_state="ABSENT",
        retained_remote_journal_inventory=[],
        artifact_states={
            "launch_transport_attempt": "ABSENT",
            "launch_admission_receipt": "ABSENT",
            "service_wrapper_attestation": "ABSENT",
        },
        recovered_documents={},
    )


def _child_fact(
    stdout_raw: bytes, *, stdin_raw: bytes | None = None,
) -> dict[str, object]:
    if stdin_raw is None:
        stdin_raw = canonical_json_bytes(
            recovery.build_recovery_transport_ingress_v42r3r4(
                recovery_plan=_plan()
            )
        )
    stdout_prefix = stdout_raw[
        : recovery.RECOVERY_TRANSPORT_CAPTURE_PREFIX_BYTES
    ]
    empty_sha = hashlib.sha256(b"").hexdigest()
    return {
        "exec_succeeded": True,
        "transport_observation_completed_without_local_error": True,
        "transport_materials_verified_after_child": True,
        "returncode": 0,
        "timed_out": False,
        "stdin_expected_byte_count": len(stdin_raw),
        "stdin_sent_byte_count": len(stdin_raw),
        "stdin_sha256": hashlib.sha256(stdin_raw).hexdigest(),
        "stdin_complete": True,
        "stdout_retained_byte_count": len(stdout_raw),
        "stdout_retained_sha256": hashlib.sha256(stdout_raw).hexdigest(),
        "stdout_prefix_byte_count": len(stdout_prefix),
        "stdout_prefix_hex": stdout_prefix.hex(),
        "stdout_total_byte_count": len(stdout_raw),
        "stdout_sha256": hashlib.sha256(stdout_raw).hexdigest(),
        "stdout_overflow": False,
        "stdout_eof": True,
        "stderr_prefix_byte_count": 0,
        "stderr_prefix_hex": "",
        "stderr_total_byte_count": 0,
        "stderr_sha256": empty_sha,
        "stderr_overflow": False,
        "stderr_eof": True,
    }


@lru_cache(maxsize=1)
def _observation() -> dict[str, object]:
    inspection_raw = canonical_json_bytes(_absent_remote_inspection()) + b"\n"
    return recovery.build_bounded_child_transport_observation_v42r3r4(
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        child_observation=_child_fact(inspection_raw),
    )


@lru_cache(maxsize=1)
def _join() -> dict[str, object]:
    return recovery.build_remote_inspection_join_v42r3r4(
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        bounded_child_transport_observation=_observation(),
        remote_read_only_inspection=_absent_remote_inspection(),
    )


def test_complete_retained_occurrence_is_exact_and_permanently_nonreplayable() -> None:
    occurrence = _occurrence()
    assert occurrence["retained_formal_transport_plan_id"] == (
        recovery.RETAINED_FORMAL_TRANSPORT_PLAN_ID
    )
    assert occurrence["retained_network_start_marker_present"] is True
    assert occurrence["retained_exact_transport_receipt_present"] is False
    assert occurrence["retained_same_effect_dispatch_replay_allowed"] is False
    assert occurrence["retained_historical_execution_status"] == (
        "UNKNOWN_NOT_INFERRED"
    )
    assert occurrence[
        "current_remote_absence_is_historical_never_started_proof"
    ] is False
    assert occurrence["retained_controller_source_manifest_id"] == (
        recovery.RETAINED_CONTROLLER_SOURCE_MANIFEST_ID
    )
    assert occurrence["retained_prepare_receipt_id"] == (
        recovery.RETAINED_PREPARE_RECEIPT_ID
    )
    assert occurrence["inner_and_parent_network_start_bytes_identical"] is True
    assert recovery.verify_retained_launch_occurrence_v42r3r4(
        canonical_json_bytes(occurrence)
    ) == occurrence


def test_embedded_retained_documents_match_current_frozen_golden_if_present() -> None:
    if not all((_FROZEN_ROOT / name).is_file() for name in _RETAINED_FILENAMES):
        pytest.skip("current production frozen root is not mounted")
    embedded = _embedded_retained_raw()
    for name in _RETAINED_FILENAMES:
        path = _FROZEN_ROOT / name
        assert path.read_bytes() == embedded[name]
        assert path.stat().st_mode & 0o777 == 0o400
        assert path.stat().st_nlink == 1


def test_controller_manifest_binds_required_roles_and_rejects_inventory_drift() -> None:
    manifest = _manifest()
    by_path = {
        row["relative_path"]: row for row in manifest["source_facts"]
    }
    assert manifest["recovery_bootstrap_artifact"] == by_path[
        recovery.RECOVERY_BOOTSTRAP_RELATIVE
    ]
    assert manifest["recovery_launcher_artifact"] == by_path[
        recovery.RECOVERY_LAUNCHER_RELATIVE
    ]
    assert manifest["recovery_receiver_artifact"] == by_path[
        recovery.RECOVERY_RECEIVER_RELATIVE
    ]
    assert manifest["recovery_authority_artifact"] == by_path[
        recovery.RECOVERY_AUTHORITY_RELATIVE
    ]
    assert recovery.verify_recovery_controller_source_manifest_v42r3r4(
        canonical_json_bytes(manifest)
    ) == manifest

    missing = list(manifest["source_facts"])[1:]
    with pytest.raises(recovery.V42FormalTransportRecoveryError):
        recovery.build_recovery_controller_source_manifest_v42r3r4(
            source_commit="a" * 40,
            source_tree="b" * 40,
            source_facts=missing,
        )
    unsorted = list(manifest["source_facts"])
    unsorted[0], unsorted[1] = unsorted[1], unsorted[0]
    with pytest.raises(recovery.V42FormalTransportRecoveryError):
        recovery.build_recovery_controller_source_manifest_v42r3r4(
            source_commit="a" * 40,
            source_tree="b" * 40,
            source_facts=unsorted,
        )


def test_recovery_plan_and_attempt_authorize_only_one_read_only_transport() -> None:
    plan = _plan()
    attempt = _attempt()
    assert plan["authenticated_remote_filesystem_mutation_authorized"] is False
    assert plan["authenticated_systemd_lifecycle_mutation_authorized"] is False
    assert plan["retained_same_effect_dispatch_replay_allowed"] is False
    assert plan["new_scientific_execution_authorized"] is False
    assert plan["recovery_inspection_ordinal"] == 1
    assert plan["authorized_remote_modes"] == [recovery.RECOVERY_REMOTE_MODE]
    assert plan["recovery_receiver_artifact"] == (
        _manifest()["recovery_receiver_artifact"]
    )
    ingress = recovery.build_recovery_transport_ingress_v42r3r4(
        recovery_plan=plan
    )
    ingress_raw = canonical_json_bytes(ingress)
    assert attempt["canonical_remote_ingress"] == ingress
    assert attempt["canonical_remote_ingress_fact"] == {
        "byte_count": len(ingress_raw),
        "sha256": hashlib.sha256(ingress_raw).hexdigest(),
    }
    projection = attempt["remote_command_projection"]
    semantics = projection["ordered_remote_python_argv_semantics"]
    assert semantics[-1] == {"recovery_plan_id": plan["recovery_plan_id"]}
    assert semantics[-1] != {
        "recovery_plan_id": recovery.RETAINED_FORMAL_TRANSPORT_PLAN_ID
    }
    assert attempt["controller_same_recovery_dispatch_replay_allowed"] is False
    assert recovery.verify_recovery_plan_v42r3r4(
        canonical_json_bytes(plan)
    ) == plan
    assert recovery.verify_recovery_inspection_attempt_v42r3r4(
        canonical_json_bytes(attempt), recovery_plan=plan
    ) == attempt


def test_bounded_transport_observation_precedes_receipt_authentication() -> None:
    observation = _observation()
    assert observation["process_closed_exactly"] is True
    assert observation[
        "observation_persisted_before_remote_receipt_acceptance_required"
    ] is True
    assert observation[
        "formal_remote_inspection_authenticated_by_this_observation"
    ] is False
    assert observation["controller_same_recovery_dispatch_replay_allowed"] is False
    assert recovery.verify_bounded_child_transport_observation_v42r3r4(
        canonical_json_bytes(observation),
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
    ) == observation

    changed = copy.deepcopy(observation["child_observation"])
    changed["stdout_prefix_hex"] = "00" + changed["stdout_prefix_hex"][2:]
    with pytest.raises(recovery.V42FormalTransportRecoveryError):
        recovery.build_bounded_child_transport_observation_v42r3r4(
            recovery_plan=_plan(),
            recovery_inspection_attempt=_attempt(),
            child_observation=changed,
        )

    wrong_ingress = copy.deepcopy(observation["child_observation"])
    wrong_ingress["stdin_sha256"] = "f" * 64
    with pytest.raises(
        recovery.V42FormalTransportRecoveryError,
        match="authorized canonical ingress",
    ):
        recovery.build_bounded_child_transport_observation_v42r3r4(
            recovery_plan=_plan(),
            recovery_inspection_attempt=_attempt(),
            child_observation=wrong_ingress,
        )

    unverified_materials = copy.deepcopy(observation["child_observation"])
    unverified_materials["transport_materials_verified_after_child"] = False
    nonexact = recovery.build_bounded_child_transport_observation_v42r3r4(
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        child_observation=unverified_materials,
    )
    assert nonexact["process_closed_exactly"] is False


def test_remote_join_and_classification_never_use_absence_as_history_proof() -> None:
    join = _join()
    assert join["authenticated_remote_inspection_stdout_exactly_joined"] is True
    assert join[
        "authenticated_body_remote_filesystem_mutation_performed"
    ] is False
    assert join["end_to_end_remote_mutation_absence_claimed"] is False
    assert recovery.verify_remote_inspection_join_v42r3r4(
        canonical_json_bytes(join),
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        bounded_child_transport_observation=_observation(),
    ) == join

    classification = recovery.classify_recovery_v42r3r4(
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        bounded_child_transport_observation=_observation(),
        remote_inspection_join=join,
    )
    assert classification["classification"] == (
        recovery.RECOVERY_CLASS_AMBIGUOUS_PERMANENTLY_CLOSED
    )
    assert classification["reason_codes"] == [
        recovery.RECOVERY_REASON_RETAINED_POST_MARKER_WITHOUT_EXACT_RECEIPT,
        recovery.RECOVERY_REASON_LAUNCH_STATE_NOT_EXACT_OR_SUPERVISION_LOST,
    ]
    assert classification["current_unit_absent"] is True
    assert classification["current_formal_journal_absent"] is True
    assert classification[
        "current_remote_absence_is_historical_never_started_proof"
    ] is False
    assert classification["retained_historical_execution_status"] == (
        "UNKNOWN_NOT_INFERRED"
    )
    assert classification["retained_same_effect_dispatch_replay_allowed"] is False
    assert classification["new_scientific_execution_authorized"] is False
    assert recovery.verify_recovery_classification_v42r3r4(
        canonical_json_bytes(classification),
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        bounded_child_transport_observation=_observation(),
        remote_inspection_join=join,
    ) == classification


def test_nonexact_transport_still_closes_retained_effect_without_history_claim() -> None:
    empty_sha = hashlib.sha256(b"").hexdigest()
    request = canonical_json_bytes(
        recovery.build_recovery_transport_ingress_v42r3r4(
            recovery_plan=_plan()
        )
    )
    failed_child = {
        "exec_succeeded": False,
        "transport_observation_completed_without_local_error": True,
        "transport_materials_verified_after_child": True,
        "returncode": None,
        "timed_out": False,
        "stdin_expected_byte_count": len(request),
        "stdin_sent_byte_count": 0,
        "stdin_sha256": hashlib.sha256(request).hexdigest(),
        "stdin_complete": False,
        "stdout_retained_byte_count": 0,
        "stdout_retained_sha256": empty_sha,
        "stdout_prefix_byte_count": 0,
        "stdout_prefix_hex": "",
        "stdout_total_byte_count": 0,
        "stdout_sha256": empty_sha,
        "stdout_overflow": False,
        "stdout_eof": False,
        "stderr_prefix_byte_count": 0,
        "stderr_prefix_hex": "",
        "stderr_total_byte_count": 0,
        "stderr_sha256": empty_sha,
        "stderr_overflow": False,
        "stderr_eof": False,
    }
    observation = recovery.build_bounded_child_transport_observation_v42r3r4(
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        child_observation=failed_child,
    )
    classification = recovery.classify_recovery_v42r3r4(
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        bounded_child_transport_observation=observation,
        remote_inspection_join=None,
    )
    assert observation["process_closed_exactly"] is False
    assert classification["reason_codes"] == [
        recovery.RECOVERY_REASON_RETAINED_POST_MARKER_WITHOUT_EXACT_RECEIPT,
        recovery.RECOVERY_REASON_INSPECTION_NOT_EXACT,
    ]
    assert classification["current_unit_absent"] is None
    assert classification[
        "current_remote_absence_is_historical_never_started_proof"
    ] is False
    assert classification["retained_same_effect_dispatch_replay_allowed"] is False


def test_all_content_identifiers_fail_closed_on_mutation() -> None:
    occurrence = _occurrence()
    changed = copy.deepcopy(occurrence)
    changed["retained_historical_execution_status"] = "NEVER_STARTED"
    with pytest.raises(recovery.V42FormalTransportRecoveryError):
        recovery.verify_retained_launch_occurrence_v42r3r4(changed)

    classification = recovery.classify_recovery_v42r3r4(
        recovery_plan=_plan(),
        recovery_inspection_attempt=_attempt(),
        bounded_child_transport_observation=_observation(),
        remote_inspection_join=_join(),
    )
    classification["current_remote_absence_is_historical_never_started_proof"] = (
        True
    )
    with pytest.raises(recovery.V42FormalTransportRecoveryError):
        recovery.verify_recovery_classification_v42r3r4(
            classification,
            recovery_plan=_plan(),
            recovery_inspection_attempt=_attempt(),
            bounded_child_transport_observation=_observation(),
            remote_inspection_join=_join(),
        )
