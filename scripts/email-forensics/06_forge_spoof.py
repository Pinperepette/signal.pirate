#!/usr/bin/env python3
"""
06_forge_spoof.py — Genera una mail spoofata per testare il detector

Crea un file .eml con header volutamente spoofati:
- From: finto (es. Netflix)
- Return-Path: su un dominio diverso
- IP nel Received: non autorizzato
- DKIM assente
- HELO mismatch

Poi la confronti con la mail Netflix vera usando 04_spoof_detector.py

Uso:
    python3 06_forge_spoof.py                          # genera spoofed.eml
    python3 06_forge_spoof.py --output phishing.eml    # nome custom
    python3 04_spoof_detector.py spoofed.eml           # analizza

NOTA: laboratorio educativo. La mail viene salvata come file locale,
non viene inviata a nessuno.
"""

import sys
import os
from datetime import datetime, timezone


GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'


def generate_spoofed_eml(output_path):
    """Genera una mail spoofata che finge di essere Netflix."""

    now = datetime.now(timezone.utc)
    date_str = now.strftime('%a, %d %b %Y %H:%M:%S +0000')

    # Header costruiti per simulare uno spoofing realistico
    eml = f"""Return-Path: <bounce-notif@cheapvps-hosting.ru>
Delivered-To: pinperepette@gmail.com
Received: from mail.netflix.com (vps-47293.cheapvps-hosting.ru. [91.202.54.17])
        by mx.google.com with SMTP id fake123456789.2026.03.10.08.30.00
        for <pinperepette@gmail.com>;
        {date_str}
Received-SPF: fail (google.com: domain of info@members.netflix.com does not designate 91.202.54.17 as permitted sender) client-ip=91.202.54.17;
Authentication-Results: mx.google.com;
        spf=fail (google.com: domain of info@members.netflix.com does not designate 91.202.54.17 as permitted sender)
        smtp.mailfrom=bounce-notif@cheapvps-hosting.ru;
        dkim=none;
        dmarc=fail (p=REJECT sp=REJECT dis=NONE) header.from=members.netflix.com
X-Mailer: PHPMailer 6.8.1
From: Netflix <info@members.netflix.com>
To: pinperepette@gmail.com
Subject: Il tuo account Netflix e' stato sospeso
Date: {date_str}
Message-ID: <fake-{now.strftime('%Y%m%d%H%M%S')}@cheapvps-hosting.ru>
MIME-Version: 1.0
Content-Type: multipart/alternative;
        boundary="----=_boundary_spoofed_001"

------=_boundary_spoofed_001
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: quoted-printable

Gentile cliente,

Il tuo account Netflix e' stato temporaneamente sospeso per un problema
con il metodo di pagamento.

Per riattivare il servizio, aggiorna i tuoi dati di pagamento:
https://netflix-verify-account.cheapvps-hosting.ru/update

Se non aggiorni entro 24 ore, il tuo account verra' cancellato.

Cordiali saluti,
Il team Netflix

------=_boundary_spoofed_001
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: quoted-printable

<html>
<body style=3D"font-family: Arial, sans-serif; background: #000; color: #fff; padding: 20px;">
<div style=3D"max-width: 600px; margin: 0 auto;">
<img src=3D"https://cheapvps-hosting.ru/img/netflix-logo-fake.png" width=3D"120">
<h2 style=3D"color: #e50914;">Il tuo account e' stato sospeso</h2>
<p>Gentile cliente,</p>
<p>Il tuo account Netflix e' stato temporaneamente sospeso per un problema
con il metodo di pagamento.</p>
<p><a href=3D"https://netflix-verify-account.cheapvps-hosting.ru/update"
   style=3D"background: #e50914; color: #fff; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
   Aggiorna i dati di pagamento
</a></p>
<p style=3D"font-size: 12px; color: #666;">Se non aggiorni entro 24 ore, il tuo account verra' cancellato.</p>
<img src=3D"https://cheapvps-hosting.ru/px/track-pinperepette-abc123.gif" width=3D"1" height=3D"1" style=3D"display:none">
</div>
</body>
</html>
------=_boundary_spoofed_001--
"""

    with open(output_path, 'w') as f:
        f.write(eml)

    return eml


def generate_legit_eml(output_path):
    """Genera una mail che simula header legittimi Netflix (per confronto)."""

    now = datetime.now(timezone.utc)
    date_str = now.strftime('%a, %d %b %Y %H:%M:%S +0000')

    eml = f"""Return-Path: <010f019cd311cd31-a2794052-5e37-4e5c-96c3-3928ab0074db-000000@mailer.members.netflix.com>
Delivered-To: pinperepette@gmail.com
Received: from a114-85.smtp-out.us-east-2.amazonses.com (a114-85.smtp-out.us-east-2.amazonses.com. [54.240.114.85])
        by mx.google.com with ESMTPS id af79cd13be357-8cd7d79d628.2026.03.09.07.48.05
        for <pinperepette@gmail.com>
        (version=TLS1_3 cipher=TLS_AES_128_GCM_SHA256 bits=128/128);
        {date_str}
DKIM-Signature: v=1; a=rsa-sha256; q=dns/txt; c=relaxed/simple;
        s=22seek5htn6zhuvy5jwo2o764amigf2d; d=members.netflix.com; t=1773067685;
        h=Date:From:To:Message-ID:Subject:MIME-Version:Content-Type;
        bh=pTEUbdZ+NOTVByxB/vvLsRNSa8RpZP7/YMIoSG5OrNg=;
        b=HNNYMI2i0vXIDpwahJ0aoSERfKZga9xxD8r8ZBgtQgsDOtoHtqRpcLh8V4lPzQc
DKIM-Signature: v=1; a=rsa-sha256; q=dns/txt; c=relaxed/simple;
        s=ndjes4mrtuzus6qxu3frw3ubo3gpjndv; d=amazonses.com; t=1773067685;
        bh=pTEUbdZ+NOTVByxB/vvLsRNSa8RpZP7/YMIoSG5OrNg=;
        b=M/CQ8v30fakesignaturefordemopurposes
Received-SPF: pass (google.com: domain of 010f019cd311cd31-a2794052-5e37-4e5c-96c3-3928ab0074db-000000@mailer.members.netflix.com designates 54.240.114.85 as permitted sender) client-ip=54.240.114.85;
Authentication-Results: mx.google.com;
        dkim=pass header.i=@members.netflix.com header.s=22seek5htn6zhuvy5jwo2o764amigf2d header.b=HNNYMI2i0;
        dkim=pass header.i=@amazonses.com header.s=ndjes4mrtuzus6qxu3frw3ubo3gpjndv header.b="M/CQ8v30";
        spf=pass (google.com: domain of 010f019cd311cd31@mailer.members.netflix.com designates 54.240.114.85)
        smtp.mailfrom=010f019cd311cd31-a2794052-5e37-4e5c-96c3-3928ab0074db-000000@mailer.members.netflix.com;
        dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=netflix.com
X-SES-Outgoing: 2026.03.09-54.240.114.85
X-SourceAppName: MSG_ORCHESTRATOR
X-LocaleCountry: it-IT::IT
From: Netflix <info@members.netflix.com>
To: pinperepette@gmail.com
Subject: pinperepette, ecco i contenuti in arrivo su Netflix
Date: {date_str}
Message-ID: <010f019cd311cd31-a2794052-5e37-4e5c-96c3-3928ab0074db-000000@us-east-2.amazonses.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8

Dai il benvenuto ai nuovi titoli che pensiamo potrebbero piacerti.
"""

    with open(output_path, 'w') as f:
        f.write(eml)

    return eml


def main():
    output_spoof = 'spoofed.eml'
    output_legit = 'legit.eml'

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '--output' and i + 1 < len(sys.argv):
            output_spoof = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    # Genera entrambe
    generate_spoofed_eml(output_spoof)
    output_legit = output_spoof.replace('spoofed', 'legit').replace('.eml', '-legit.eml')
    if output_legit == output_spoof:
        output_legit = 'legit.eml'
    generate_legit_eml(output_legit)

    print(f'\n{BOLD}{"=" * 60}{RESET}')
    print(f'{BOLD}  MAIL SPOOFATA + LEGITTIMA GENERATE{RESET}')
    print(f'{BOLD}{"=" * 60}{RESET}\n')

    print(f'  {RED}Spoofata:{RESET}  {output_spoof}')
    print(f'  {DIM}  From: Netflix <info@members.netflix.com>{RESET}')
    print(f'  {DIM}  Ma: Return-Path russo, IP non autorizzato,{RESET}')
    print(f'  {DIM}  niente DKIM, X-Mailer: PHPMailer 6.8.1{RESET}')
    print(f'  {DIM}  + tracking pixel nascosto nell\'HTML{RESET}')
    print()
    print(f'  {GREEN}Legittima:{RESET} {output_legit}')
    print(f'  {DIM}  From: Netflix <info@members.netflix.com>{RESET}')
    print(f'  {DIM}  Return-Path Netflix, IP Amazon SES,{RESET}')
    print(f'  {DIM}  doppia firma DKIM, DMARC pass{RESET}')
    print()
    print(f'  {BOLD}Ora lancia il detector su entrambe:{RESET}')
    print(f'  {CYAN}python3 04_spoof_detector.py {output_spoof}{RESET}')
    print(f'  {CYAN}python3 04_spoof_detector.py {output_legit}{RESET}')
    print()
    print(f'  {BOLD}E il pixel hunter sulla spoofata:{RESET}')
    print(f'  {CYAN}python3 05_pixel_hunter.py {output_spoof}{RESET}')
    print(f'\n{BOLD}{"=" * 60}{RESET}\n')


if __name__ == '__main__':
    main()
