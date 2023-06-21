from .wfs import WFSImporter


class PaavoImporter(WFSImporter):
    id = 'paavo'
    name = 'Stat.fi Paavo WFS'
    wfs_url = 'https://geo.stat.fi/geoserver/postialue/wfs'

    area_types = {
        'fi:paavo': dict(name='Postinumeroalueet'),
    }

    def filter_feature(self, identifier: str, feat: dict) -> bool:
        return True

    def get_area_types(self):
        return self.area_types

    def get_props_meta(self):
        meta_lines = [x.split() for x in META.strip().splitlines()]
        meta = {x[0]: ' '.join(x[1:]) for x in meta_lines}
        return meta

    def read_post_areas(self, identifier: str) -> dict:
        layer_name = 'postialue:pno_tilasto'

        META_REMOVE = ('namn', 'euref_x', 'euref_y', 'kunta',)
        props_meta = self.get_props_meta()
        del props_meta['nimi']
        del props_meta['posti_alue']

        for p in META_REMOVE:
            del props_meta[p]

        d = self.read_wfs_layer(layer_name)
        areas = []
        for feat in d['features']:
            props = feat['properties']
            id = props.pop('postinumeroalue')
            name = props.pop('nimi')
            props.pop('bbox', None)
            for p in META_REMOVE:
                del props[p]
            out = dict(identifier=id, name=name, geometry=feat['geometry'], properties=props)
            if not self.filter_feature(identifier, out):
                continue
            areas.append(out)

        return dict(areas=areas, properties_meta=props_meta)

    def read_area_type(self, identifier) -> dict:
        conf = self.area_types[identifier]
        out = self.read_post_areas(identifier)
        out['identifier'] = identifier
        out['name'] = conf['name']
        return out


META = """
posti_alue Postinumeroalue
nimi Postinumeroalueen nimi suomeksi
namn Postinumeroalueen nimi ruotsiksi
euref_x X-koordinaatti
euref_y Y-koordinaatti
pinta_ala Postinumeroalueen pinta-ala (m2)
vuosi Paavo-postinumeroaluetilastojen julkaisuvuosi
kunta Kunta 1.1.2022
he_vakiy Asukkaat yhteensä, 2020 (HE)
he_miehet Miehet, 2020 (HE)
he_naiset Naiset, 2020 (HE)
he_kika Asukkaiden keski-ikä, 2020 (HE)
he_0_2 0–2-vuotiaat, 2020 (HE)
he_3_6 3–6-vuotiaat, 2020 (HE)
he_7_12 7–12-vuotiaat, 2020 (HE)
he_13_15 13–15-vuotiaat, 2020 (HE)
he_16_17 16–17-vuotiaat, 2020 (HE)
he_18_19 18–19-vuotiaat, 2020 (HE)
he_20_24 20–24-vuotiaat, 2020 (HE)
he_25_29 25–29-vuotiaat, 2020 (HE)
he_30_34 30–34-vuotiaat, 2020 (HE)
he_35_39 35–39-vuotiaat, 2020 (HE)
he_40_44 40–44-vuotiaat, 2020 (HE)
he_45_49 45–49-vuotiaat, 2020 (HE)
he_50_54 50–54-vuotiaat, 2020 (HE)
he_55_59 55–59-vuotiaat, 2020 (HE)
he_60_64 60–64-vuotiaat, 2020 (HE)
he_65_69 65–69-vuotiaat, 2020 (HE)
he_70_74 70–74-vuotiaat, 2020 (HE)
he_75_79 75–79-vuotiaat, 2020 (HE)
he_80_84 80–84-vuotiaat, 2020 (HE)
he_85_ 85 vuotta täyttäneet, 2020 (HE)
ko_ika18y 18 vuotta täyttäneet yhteensä, 2020 (KO)
ko_perus Perusasteen suorittaneet, 2020 (KO)
ko_koul Koulutetut yhteensä, 2020 (KO)
ko_yliop Ylioppilastutkinnon suorittaneet, 2020 (KO)
ko_ammat Ammatillisen tutkinnon suorittaneet, 2020 (KO)
ko_al_kork Alemman korkeakoulututkinnon suorittaneet, 2020 (KO)
ko_yl_kork Ylemmän korkeakoulututkinnon suorittaneet, 2020 (KO)
hr_tuy 18 vuotta täyttäneet yhteensä, 2020 (HR)
hr_ktu Asukkaiden keskitulot, 2020 (HR)
hr_mtu Asukkaiden mediaanitulot, 2020 (HR)
hr_pi_tul Alimpaan tuloluokkaan kuuluvat asukkaat, 2020 (HR)
hr_ke_tul Keskimmäiseen tuloluokkaan kuuluvat asukkaat, 2020 (HR)
hr_hy_tul Ylimpään tuloluokkaan kuuluvat asukkaat, 2020 (HR)
hr_ovy Asukkaiden ostovoimakertymä, 2020 (HR)
te_taly Taloudet yhteensä, 2020 (TE)
te_takk Talouksien keskikoko, 2020 (TE)
te_as_valj Asumisväljyys, 2020 (TE)
te_yks Yksinasuvien taloudet, 2020 (TE)
te_nuor Nuorten yksinasuvien taloudet, 2020 (TE)
te_eil_np Lapsettomat nuorten parien taloudet, 2020 (TE)
te_laps Lapsitaloudet, 2020 (TE)
te_plap Pienten lasten taloudet, 2020 (TE)
te_aklap Alle kouluikäisten lasten taloudet, 2020 (TE)
te_klap Kouluikäisten lasten taloudet, 2020 (TE)
te_teini Teini-ikäisten lasten taloudet, 2020 (TE)
te_yhlap Yhden vanhemman lapsitaloudet, 2020 (TE)
te_aik Aikuisten taloudet, 2020 (TE)
te_elak Eläkeläisten taloudet, 2020 (TE)
te_omis_as Omistusasunnoissa asuvat taloudet, 2020 (TE)
te_vuok_as Vuokra- ja asumisoikeusasunnoissa asuvat taloudet, 2020 (TE)
te_muu_as Muissa asunnoissa asuvat taloudet, 2020 (TE)
tr_kuty Taloudet yhteensä, 2020 (TR)
tr_ktu Talouksien keskitulot, 2020 (TR)
tr_mtu Talouksien mediaanitulot, 2020 (TR)
tr_pi_tul Alimpaan tuloluokkaan kuuluvat taloudet, 2020 (TR)
tr_ke_tul Keskimmäiseen tuloluokkaan kuuluvat taloudet, 2020 (TR)
tr_hy_tul Ylimpään tuloluokkaan kuuluvat taloudet, 2020 (TR)
tr_ovy Talouksien ostovoimakertymä, 2020 (TR)
ra_ke Kesämökit yhteensä, 2020 (RA)
ra_raky Rakennukset yhteensä, 2020 (RA)
ra_muut Muut rakennukset yhteensä, 2020 (RA)
ra_asrak Asuinrakennukset yhteensä, 2020 (RA)
ra_asunn Asunnot, 2020 (RA)
ra_as_kpa Asuntojen keskipinta-ala, 2020 (RA)
ra_pt_as Pientaloasunnot, 2020 (RA)
ra_kt_as Kerrostaloasunnot, 2020 (RA)
ra_muu_as Muut asunnot, 2020 (RA)
tp_tyopy Työpaikat yhteensä, 2019 (TP)
tp_alku_a Alkutuotannon työpaikat, 2019 (TP)
tp_jalo_bf Jalostuksen työpaikat, 2019 (TP)
tp_palv_gu Palveluiden työpaikat, 2019 (TP)
tp_a_maat A Maatalous, metsätalous ja kalatalous, 2019 (TP)
tp_b_kaiv B Kaivostoiminta ja louhinta, 2019 (TP)
tp_c_teol C Teollisuus, 2019 (TP)
tp_d_ener D Sähkö-, kaasu- ja lämpöhuolto, jäähdytysliiketoiminta, 2019 (TP)
tp_e_vesi E Vesihuolto, viemäri- ja jätevesihuolto ja muu ympäristön puhtaanapito, 2019 (TP)
tp_f_rake F Rakentaminen, 2019 (TP)
tp_g_kaup G Tukku- ja vähittäiskauppa; moottoriajoneuvojen ja moottoripyörien korjaus, 2019 (TP)
tp_h_kulj H Kuljetus ja varastointi, 2019 (TP)
tp_i_majo I Majoitus- ja ravitsemistoiminta, 2019 (TP)
tp_j_info J Informaatio ja viestintä, 2019 (TP)
tp_k_raho K Rahoitus- ja vakuutustoiminta, 2019 (TP)
tp_l_kiin L Kiinteistöalan toiminta, 2019 (TP)
tp_m_erik M Ammatillinen, tieteellinen ja tekninen toiminta, 2019 (TP)
tp_n_hall N Hallinto- ja tukipalvelutoiminta, 2019 (TP)
tp_o_julk O Julkinen hallinto ja maanpuolustus; pakollinen sosiaalivakuutus, 2019 (TP)
tp_p_koul P Koulutus, 2019 (TP)
tp_q_terv Q Terveys- ja sosiaalipalvelut, 2019 (TP)
tp_r_taid R Taiteet, viihde ja virkistys, 2019 (TP)
tp_s_muup S Muu palvelutoiminta, 2019 (TP)
tp_t_koti T Kotitalouksien toiminta työnantajina; kotitalouksien eriyttämätön toiminta tavaroiden ja palveluiden tuottamiseksi omaan käyttöön, 2019 (TP)
tp_u_kans U Kansainvälisten organisaatioiden ja toimielinten toiminta, 2019 (TP)
tp_x_tunt X Toimiala tuntematon, 2019 (TP)
pt_vakiy Asukkaat yhteensä, 2019 (PT)
pt_tyoll Työlliset, 2019 (PT)
pt_tyott Työttömät, 2019 (PT)
pt_0_14 Lapset 0–14-vuotiaat, 2019 (PT)
pt_opisk Opiskelijat, 2019 (PT)
pt_elakel Eläkeläiset, 2019 (PT)
pt_muut Muut, 2019 (PT)
"""
