import streamlit as st
import eval7

# --- 1. 핵심 분석 엔진 ---
def calculate_precise_stats(hero_hand, board, iters=3000):
    try:
        if len(hero_hand) < 2: return 0.0
        hero_c = [eval7.Card(c) for c in hero_hand]
        board_c = [eval7.Card(c) for c in board]
        win_count = 0
        for _ in range(iters):
            deck = eval7.Deck()
            for c in hero_c + board_c:
                if c in deck.cards: deck.cards.remove(c)
            deck.shuffle()
            opp_cards = deck.deal(2)
            temp_board = board_c + deck.deal(5 - len(board_c))
            h_s = eval7.evaluate(hero_c + temp_board)
            o_s = eval7.evaluate(opp_cards + temp_board)
            if h_s > o_s: win_count += 1
            elif h_s == o_s: win_count += 0.5
        return (win_count / iters) * 100
    except: return 0.0

def get_positions(total):
    full_ring = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"]
    if total == 2: return ["BTN/SB", "BB"]
    return full_ring[-total:]

def get_differentiated_advice(equity, pot_odds, stack, icm_mode, stage, hero_pos, hero_act):
    is_pf = stack <= 12
    advices = []
    if is_pf:
        threshold = pot_odds + 5.0
        mode_title = "⚔️ [PUSH/FOLD STRATEGY]"
        advices.append("- 숏스택 상황: 폴드 에퀴티를 활용한 올인 전략이 우선입니다.")
    elif icm_mode:
        threshold = pot_odds + 10.0
        mode_title = "🏆 [ICM SURVIVAL STRATEGY]"
        advices.append("- 생존 우선: 칩 확보보다 탈락 방지가 최우선입니다.")
    else:
        threshold = pot_odds
        mode_title = "🟢 [STANDARD GTO STRATEGY]"
    
    if hero_pos in ["SB", "BB"] and stage != "Pre-flop":
        advices.append("- 📍 OOP: 포지션이 불리하므로 방어적인 체크-콜 레인지를 구성하세요.")
    
    return advices, threshold, mode_title

# --- 2. UI 세션 관리 ---
st.set_page_config(page_title="Pro Poker Advisor", layout="centered")

if 'step' not in st.session_state:
    st.session_state.update({
        'step': 1, 'hero_hand': [], 'board': [], 'folded': [], 
        'villain_sizes': {}, 'hero_action': "None", 'hero_bet_size': 0.0,
        'stage': "Pre-flop", 'icm_mode': False, 'hero_pos': "BTN", 
        'total': 9, 'hero_stack': 30.0, 'acc_pot': 1.5
    })

# --- 3. 프리미엄 대시보드 ---
def display_dashboard(current_total_pot, pot_odds):
    stack = st.session_state.hero_stack
    mode_color = "#ff4b4b" if stack <= 12 else ("#ffcc00" if st.session_state.icm_mode else "#28a745")
    st.markdown(f"""
        <div style="background-color:{mode_color}; padding:10px; border-radius:8px; text-align:center; color:white; font-weight:bold; margin-bottom:15px;">
            STAGE: {st.session_state.stage} | STACK: {stack:.1f} BB
        </div>
        <div style="background-color:#1e1e1e; padding:20px; border-radius:12px; border: 1px solid #444; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <small style="color:#888;">CURRENT POT</small><br>
                    <span style="font-size:24px; color:#4caf50; font-weight:bold;">{current_total_pot:.1f} BB</span>
                </div>
                <div style="text-align:right;">
                    <small style="color:#888;">POT ODDS (REQ. EQ)</small><br>
                    <span style="font-size:24px; color:#f44336; font-weight:bold;">{pot_odds:.1f}%</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 4. 메인 단계 로직 ---

# STEP 1: 설정
if st.session_state.step == 1:
    st.title("🏆 Tournament Setup")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.hero_stack = st.number_input("내 스택 (BB)", min_value=1.0, value=30.0)
        st.session_state.total = st.select_slider("인원수", options=range(2, 10), value=9)
    with c2:
        p_list = get_positions(st.session_state.total)
        st.session_state.hero_pos = st.selectbox("나의 포지션", p_list, index=max(0, len(p_list)-3))
        st.session_state.icm_mode = st.toggle("ICM 모드 활성화")
    if st.button("게임 시작 ➡️"): st.session_state.step = 2; st.rerun()

# STEP 2: 액션 입력 (순서 변경됨)
elif st.session_state.step == 2:
    st.title(f"🎰 Step 1: {st.session_state.stage} Actions")
    p_list = get_positions(st.session_state.total)
    
    current_round_bets = sum(st.session_state.villain_sizes.values()) + st.session_state.hero_bet_size
    temp_total_pot = st.session_state.acc_pot + current_round_bets
    max_v_bet = max(st.session_state.villain_sizes.values()) if st.session_state.villain_sizes else 0
    to_call = max(0, max_v_bet - st.session_state.hero_bet_size)
    pot_odds = (to_call / (temp_total_pot + to_call)) * 100 if to_call > 0 else 0
    
    display_dashboard(temp_total_pot, pot_odds)
    
    for p in p_list:
        c1, c2, c3, c4 = st.columns([1, 1, 2, 1.5])
        if p == st.session_state.hero_pos:
            c1.warning("**HERO**")
            st.session_state.hero_action = c3.selectbox("내 액션", ["None", "Check", "Call", "Bet/Raise", "Fold"], key="h_a")
            if st.session_state.hero_action == "Bet/Raise":
                st.session_state.hero_bet_size = c4.number_input("BB", min_value=0.0, step=0.5, key="h_s")
            elif st.session_state.hero_action == "Call": st.session_state.hero_bet_size = max_v_bet
            else: st.session_state.hero_bet_size = 0.0
            continue
        
        is_f = p in st.session_state.folded
        c1.write(f"**{p}**")
        if c2.button("Fold", key=f"f_{p}", type="primary" if is_f else "secondary"):
            if is_f: st.session_state.folded.remove(p); st.session_state.villain_sizes.pop(p, None)
            else: st.session_state.folded.append(p); st.session_state.villain_sizes[p] = 0.0
            st.rerun()
        if not is_f:
            v_act = c3.selectbox("상대 액션", ["None", "Check", "Call", "Bet/Raise", "All-in"], key=f"v_a_{p}")
            if v_act in ["Bet/Raise", "All-in"]:
                st.session_state.villain_sizes[p] = c4.number_input("BB", min_value=0.0, key=f"v_s_{p}", step=0.5, value=st.session_state.villain_sizes.get(p, 0.0))

    if st.button("액션 확정 및 카드 입력 ➡️"):
        st.session_state.acc_pot = temp_total_pot
        st.session_state.step = 3; st.rerun()

# STEP 3: 카드 입력 및 분석 (순서 변경됨)
elif st.session_state.step == 3:
    st.title(f"🃏 Step 2: {st.session_state.stage} Cards & Analysis")
    
    # 분석용 최종 팟 오즈 계산
    max_v = max(st.session_state.villain_sizes.values()) if st.session_state.villain_sizes else 0
    to_call = max(0, max_v - st.session_state.hero_bet_size)
    final_pot_odds = (to_call / (st.session_state.acc_pot + to_call)) * 100 if to_call > 0 else 0
    display_dashboard(st.session_state.acc_pot, final_pot_odds)

    c1, c2 = st.columns(2)
    def card_picker(label, target_list, max_cnt):
        st.write(f"**{label}**")
        suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}; ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
        s_key = f"s_{label}"
        scols = st.columns(4)
        for i, (sn, sv) in enumerate(suits.items()):
            if scols[i].button(sn, key=f"{s_key}_{sv}", type="primary" if st.session_state.get(s_key) == sv else "secondary"):
                st.session_state[s_key] = sv; st.rerun()
        chosen_s = st.session_state.get(s_key)
        if chosen_s:
            all_u = st.session_state.hero_hand + st.session_state.board
            for row in [ranks[:7], ranks[7:]]:
                rcols = st.columns(7)
                for i, r in enumerate(row):
                    card = f"{r}{chosen_s}"
                    is_s = card in target_list
                    if rcols[i].button(r, key=f"r_{label}_{card}", disabled=card in all_u and not is_s, type="primary" if is_s else "secondary"):
                        if is_s: target_list.remove(card)
                        elif len(target_list) < max_cnt: target_list.append(card)
                        st.rerun()

    with c1:
        if st.session_state.stage == "Pre-flop": card_picker("내 핸드 (2장)", st.session_state.hero_hand, 2)
        else: st.success(f"내 핸드: {' '.join(st.session_state.hero_hand)}")
    with c2:
        if st.session_state.stage != "Pre-flop":
            m_c = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 3)
            card_picker(f"보드 ({m_c}장)", st.session_state.board, m_c)

    # 모든 카드가 입력되었을 때만 분석 실행
    ready_to_calc = (len(st.session_state.hero_hand) == 2) and (st.session_state.stage == "Pre-flop" or len(st.session_state.board) >= {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 0))

    if ready_to_calc:
        st.divider()
        with st.spinner("EV 및 승률 시뮬레이션 중..."):
            equity = calculate_precise_stats(st.session_state.hero_hand, st.session_state.board)
        
        advices, threshold, mode_title = get_differentiated_advice(equity, final_pot_odds, st.session_state.hero_stack, st.session_state.icm_mode, st.session_state.stage, st.session_state.hero_pos, st.session_state.hero_action)
        
        st.subheader(f"🎯 분석 결과: {mode_title}")
        res1, res2 = st.columns([1, 2])
        res1.metric("실제 승률", f"{equity:.1f}%", delta=f"{equity-threshold:.1f}%")
        with res2:
            st.write(f"**필요 승률:** {threshold:.1f}%")
            for a in advices: st.info(a)
        
        if equity >= threshold: st.success("✅ **추천 액션: 플레이 유지 (Positive EV)**")
        else: st.error("🛑 **추천 액션: 폴드 고려 (Negative EV)**")

    st.divider()
    cl, cr = st.columns(2)
    if cr.button("다음 라운드로 ➡️", disabled=st.session_state.stage == "River" or st.session_state.hero_action == "Fold"):
        st.session_state.stage = ["Pre-flop", "Flop", "Turn", "River"][["Pre-flop", "Flop", "Turn", "River"].index(st.session_state.stage)+1]
        st.session_state.villain_sizes = {}
        st.session_state.hero_action, st.session_state.hero_bet_size = "None", 0.0
        st.session_state.step = 2; st.rerun()
    if cl.button("🔄 게임 리셋"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
