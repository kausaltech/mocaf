from .enums import Disease


# Amount of mMETh/wk that is needed to reduce risk with the given percentage
# RiskChange,Disease.ALL_CAUSE_MORTALITY,Disease.CARDIOVASCULAR,Disease.DEMENTIA
DISEASE_RISK_RAW = """
-0%	0	0	0
-1%	0.141395868	0.218372314	0.156464621
-2%	0.284372775	0.439176067	0.314741531
-3%	0.429106069	0.662701281	0.475096789
-4%	0.575781211	0.889261221	0.63781443
-5%	0.72459534	1.119196094	0.803200073
-6%	0.875758991	1.352877276	0.971773462
-7%	1.029498023	1.590712164	1.143772409
-8%	1.186304032	1.833149827	1.319645129
-9%	1.346480559	2.080687615	1.500133079
-10%	1.510141169	2.333878978	1.685571084
-11%	1.677615135	2.593352784	1.877006734
-12%	1.849847956	2.86004752	2.075141915
-13%	2.027134768	3.134594624	2.281096215
-14%	2.209652506	3.418298026	2.496348504
-15%	2.399350018	3.712241507	2.722779511
-16%	2.595775363	4.018078949	2.962818202
-17%	2.80153804	4.337845237	3.219728436
-18%	3.016895512	4.674003648	3.497943176
-19%	3.244397914	5.028800056	3.801591823
-20%	3.486441324	5.404944356	4.137104953
-21%	3.744478688	5.805046541	4.512775172
-22%	4.02102547	6.232870713	4.942426074
-23%	4.319821459	6.692688816	5.448697828
-24%	4.64474141	7.190434062	6.075441833
-25%	5.001310414	7.733570549	6.931968126
-26%	5.397339266	8.332374821	8.571009463
-27%	5.843813106	9.001766782	
-28%	6.359132947	9.763332104	
-29%	6.972579362	10.65233916	
-30%	7.739763013	11.73125008	
-31%	8.792170908	13.1309497	
-32%	10.57228751	15.22098026	
-33%	14.00030328	19.88667953	
-34%	17.72684488	27.38319019	
-35%	21.51028659	34.99444165	
-36%	25.3523862		
-37%	29.25499527		
-38%	33.22004885		
-39%	37.24957651		
"""


def process_raw():
    lines = DISEASE_RISK_RAW.strip('\n').splitlines()
    diseases = (Disease.ALL_CAUSE_MORTALITY, Disease.CARDIOVASCULAR, Disease.DEMENTIA)
    per_disease = {d: list() for d in diseases}
    for line in lines:
        change, *mmeths = line.split('\t')
        # Convert to daily mmeths
        mmeths = [(float(x) / 7 if x else None) for x in mmeths]
        change = int(change.strip('%'))
        for idx, d in enumerate(diseases):
            if mmeths[idx] is None:
                continue
            per_disease[d].append((mmeths[idx], change))

    return per_disease


per_disease_risk = process_raw()


def get_risk_change(disease: Disease, mmeth: float, nr_days: int):
    d = per_disease_risk[disease]
    risk_change = 0
    for val, change in d:
        if val * nr_days > mmeth:
            break
        risk_change = change
    return risk_change
