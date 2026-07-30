\# Categorical Ground Truth — Real Distinct Values
Recorded by hand from the real CSVs, Phase 0. This is what

categorical\_check.py checks against later (Phase 3). Do not trust

PROJECT.md section 2's guessed list over this file — this one is real.



\---

## order\_status (olist\_orders\_dataset.csv)

approved, canceled, created, delivered, invoiced, processing, shipped, unavailable



\## payment\_type (olist\_order\_payments\_dataset.csv)

boleto, credit\_card, debit\_card, not\_defined, voucher



\## customer\_state (olist\_customers\_dataset.csv)

AC, AL, AM, AP, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR,

RJ, RN, RO, RR, RS, SC, SE, SP, TO



Note: missing AL, AP, RR, TO compared to customer_state — no sellers
are based in these 4 states. Not a bug. A query filtering
seller_state = 'AL' (or AP, RR, TO) will correctly return zero rows.



\## seller\_state (olist\_sellers\_dataset.csv)

AC, AM, BA, CE, DF, ES, GO, MA, MG, MS, MT, PA, PB, PE, PI, PR, RJ, RN,

RO, RS, SC, SE, SP



\## product\_category\_name (olist\_products\_dataset.csv)

agro\_industria\_e\_comercio, alimentos, alimentos\_bebidas, artes,

artes\_e\_artesanato, artigos\_de\_festas, artigos\_de\_natal, audio,

automotivo, bebes, bebidas, beleza\_saude, brinquedos, cama\_mesa\_banho,

casa\_conforto, casa\_conforto\_2, casa\_construcao, cds\_dvds\_musicais,

cine\_foto, climatizacao, consoles\_games,

construcao\_ferramentas\_construcao, construcao\_ferramentas\_ferramentas,

construcao\_ferramentas\_iluminacao, construcao\_ferramentas\_jardim,

construcao\_ferramentas\_seguranca, cool\_stuff, dvds\_blu\_ray,

eletrodomesticos, eletrodomesticos\_2, eletronicos, eletroportateis,

esporte\_lazer, fashion\_bolsas\_e\_acessorios, fashion\_calcados,

fashion\_esporte, fashion\_roupa\_feminina, fashion\_roupa\_infanto\_juvenil,

fashion\_roupa\_masculina, fashion\_underwear\_e\_moda\_praia,

ferramentas\_jardim, flores, fraldas\_higiene,

industria\_comercio\_e\_negocios, informatica\_acessorios,

instrumentos\_musicais, la\_cuisine, livros\_importados,

livros\_interesse\_geral, livros\_tecnicos, malas\_acessorios,

market\_place, moveis\_colchao\_e\_estofado,

moveis\_cozinha\_area\_de\_servico\_jantar\_e\_jardim, moveis\_decoracao,

moveis\_escritorio, moveis\_quarto, moveis\_sala, musica, papelaria,

pc\_gamer, pcs, perfumaria, pet\_shop, portateis\_casa\_forno\_e\_cafe,

portateis\_cozinha\_e\_preparadores\_de\_alimentos, relogios\_presentes,

seguros\_e\_servicos, sinalizacao\_e\_seguranca, tablets\_impressao\_imagem,

telefonia, telefonia\_fixa, utilidades\_domesticas

