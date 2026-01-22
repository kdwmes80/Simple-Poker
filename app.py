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

def get_differentiated_advice(equity, pot_odds, stack, icm_mode, stage, hero_pos, hero_act, villain_sizes):
    """유실되었던 모든 조언 로직 복구 및 정교화"""
    is_pf = stack <= 12
    advices = []
    
    # 모드별 가중치 적용
    threshold = pot_odds + (10.0 if icm_mode else (5.0 if is_pf else 0))
    mode_title = "⚔️ PUSH/FOLD" if is_pf else ("🏆 ICM SURVIVAL" if icm_mode else "🟢 STANDARD GTO")

    # [조언 1] 모드별 전략
    if is_pf:
        advices.append("- **숏스택**: 복잡한 포스트플랍보다 Shove/Fold 위주로 단순화하세요.")
        if hero_act == "Call": advices.append("- ⚠️ **경고**: 숏스택에서 콜은 칩 리듬을 깨뜨립니다. 가급적 올인하세요.")
    elif icm_mode:
        advices.append("- **ICM**: 현재 칩을 지키는 가치가 얻는 가치보다 큽니다. 타이트하게 가세요.")
        if 45 <= equity <= 55: advices.append("- ⚠️ **위험**: 코인플립 승부는 ICM 관점에서 손해일 확률이 매우 높습니다.")

    # [조언 2] 포지션 및 상황
    if hero_pos in ["SB", "BB"] and stage != "Pre-flop":
        advices.append("- **포지션 불리(OOP)**: 아웃 오브 포지션입니다. 체크-콜 위주로 팟을 조절하세요.")
    
    max_v = max(villain_sizes.values() or [0])
    if max_v > 15:
        advices.append("- **고액 베팅 감지**: 상대의 레인지가 매우 강하거나 폴드 에퀴티를 노린 블러프입니다.")

    return advices, threshold, mode_title

# --- 2. UI 세션 관리 ---
st.set_page_config(page_title="Tournament Strategy Pro", layout="centered")

if 'step' not in st.session_state:
    st.session_state.update({
        'step': 1, 'hero_hand': [], 'board': [], 'folded': [], 
        'villain_sizes': {}, 'hero_action': "None", 'hero_bet_size': 0.0,
        'stage': "Pre-flop", 'icm_mode': False, 'hero_pos': "BTN", 
        'total': 9, 'hero_stack': 30.0, 'acc_pot': 1.5
    })

# --- 3. 실시간 대시보드 ---
def display_dashboard(current_total_pot, pot_odds):
    stack = st.session_state.hero_stack
    mode_color = "#ff4b4b" if stack <= 12 else ("#ffcc00" if st.session_state.icm_mode else "#28a745")
    st.markdown(f"""
        <div style="background-color:{mode_color}; padding:10px; border-radius:8px; text-align:center; color:white; font-weight:bold; margin-bottom:15px;">
            {st.session_state.stage} | {st.session_state.hero_pos} | STACK: {stack:.1f} BB
        </div>
        <div style="background-color:#1e1e1e; padding:20px; border-radius:12px; border: 1px solid #444; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <small style="color:#888;">TOTAL POT</small><br>
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
    st.title("🏆 Strategy Setup")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.hero_stack = st.number_input("내 스택 (BB)", min_value=1.0, value=30.0)
        st.session_state.total = st.select_slider("인원수", options=range(2, 10), value=9)
    with c2:
        p_list = get_positions(st.session_state.total)
        st.session_state.hero_pos = st.selectbox("나의 포지션", p_list, index=max(0, len(p_list)-3))
        st.session_state.icm_mode = st.toggle("ICM 모드 활성화")
    if st.button("게임 시작 ➡️"): st.session_state.step = 2; st.rerun()

# STEP 2: 액션 입력 (팟오즈 실시간 반영)
elif st.session_state.step == 2:
    st.title(f"🎰 Step 1: {st.session_state.stage} Actions")
    p_list = get_positions(st.session_state.total)
    
    # 팟 오즈 실시간 계산
    current_round_bets = sum(st.session_state.villain_sizes.values()) + st.session_state.hero_bet_size
    temp_total_pot = st.session_state.acc_pot + current_round_bets
    max_v_bet = max(st.session_state.villain_sizes.values() or [0])
    to_call = max(0, max_v_bet - st.session_state.hero_bet_size)
    pot_odds = (to_call / (temp_total_pot + to_call)) * 100 if (temp_total_pot + to_call) > 0 else 0
    
    display_dashboard(temp_total_pot, pot_odds)
    
    for p in p_list:
        c1, c2, c3, c4 = st.columns([1, 1, 2, 1.5])
        if p == st.session_state.hero_pos:
            c1.warning("**HERO**")
            st.session_state.hero_action = c3.selectbox("내 액션", ["None", "Check", "Call", "Bet/Raise", "Fold"], key="h_a")
            if st.session_state.hero_action == "Bet/Raise":
                st.session_state.hero_bet_size = c4.number_input("사이즈(BB)", min_value=0.0, step=0.5, key="h_s")
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

# STEP 3: 카드 입력 및 최종 승률 분석
elif st.session_state.step == 3:
    st.title(f"🃏 Step 2: {st.session_state.stage} Cards & Result")
    
    max_v = max(st.session_state.villain_sizes.values() or [0])
    to_call = max(0, max_v - st.session_state.hero_bet_size)
    final_pot_odds = (to_call / (st.session_state.acc_pot + to_call)) * 100 if (st.session_state.acc_pot + to_call) > 0 else 0
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
        else: st.success(f"핸드: {' '.join(st.session_state.hero_hand)}")
    with c2:
        if st.session_state.stage != "Pre-flop":
            m_c = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 3)
            card_picker(f"보드 ({m_c}장)", st.session_state.board, m_c)

    # 모든 데이터 입력 완료 시 분석
    ready_to_calc = (len(st.session_state.hero_hand) == 2) and (st.session_state.stage == "Pre-flop" or len(st.session_state.board) >= {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 0))

    if ready_to_calc:
        st.divider()
        with st.spinner("최첨단 시뮬레이션 계산 중..."):
            equity = calculate_precise_stats(st.session_state.hero_hand, st.session_state.board)
        
        advices, threshold, mode_title = get_differentiated_advice(equity, final_pot_odds, st.session_state.hero_stack, st.session_state.icm_mode, st.session_state.stage, st.session_state.hero_pos, st.session_state.hero_action, st.session_state.villain_sizes)
        
        st.subheader(f"📊 분석 리포트: {mode_title}")
        res1, res2 = st.columns([1, 2])
        res1.metric("실제 승률 (Equity)", f"{equity:.1f}%", delta=f"{equity-threshold:.1f}% EV")
        with res2:
            st.write(f"**타겟 승률 (보정치 포함):** {threshold:.1f}%")
            for a in advices: st.info(a)
        
        if equity >= threshold: st.success("✅ **결론: 수학적으로 유리한 상황 (CALL/RAISE 추천)**")
        else: st.error("🛑 **결론: 수학적으로 불리한 상황 (FOLD 추천)**")

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
