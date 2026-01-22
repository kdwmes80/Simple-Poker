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

def get_advanced_special_advice(equity, pot_odds, stack, stage, hero_pos, hero_act, villain_sizes, icm_mode):
    advices = []
    # [모드 진단]
    if stack <= 12:
        advices.append("⚔️ **Push/Fold 모드**: 현재 숏스택입니다. 마진한 핸드로 콜하기보다 올인으로 주도권을 가져오세요.")
    elif icm_mode:
        advices.append("🏆 **ICM 서바이벌**: 칩의 생존 가치가 높습니다. 50/50 승부는 피하고 확실한 에퀴티 우위에서만 움직이세요.")
    
    # [상황별 조언]
    max_v_bet = max(villain_sizes.values()) if villain_sizes else 0
    if max_v_bet > 0 and (equity < pot_odds):
        advices.append("🛑 **수학적 경고**: 필요 승률보다 실제 승률이 낮습니다. 블러프 가능성이 낮다면 폴드가 정답입니다.")
    if hero_pos in ["SB", "BB"] and stage != "Pre-flop":
        advices.append("📍 **포지션 주의**: 아웃 오브 포지션입니다. 체크-콜 위주보다 주도권을 뺏기지 않는 것이 중요합니다.")
    
    return advices

# --- 2. UI 세션 및 초기화 ---
st.set_page_config(page_title="Tournament Strategy Master", layout="centered")

if 'step' not in st.session_state:
    st.session_state.update({
        'step': 1, 'hero_hand': [], 'board': [], 'folded': [], 
        'villain_actions': {}, 'villain_sizes': {}, 
        'hero_action': "None", 'hero_bet_size': 0.0,
        'stage': "Pre-flop", 'icm_mode': False, 'hero_pos': "BTN", 
        'total': 9, 'hero_stack': 30.0, 'acc_pot': 1.5 # 이전 라운드 누적 팟
    })

# --- 3. 통합 대시보드 ---
def display_dashboard(current_pot, pot_odds):
    stack = st.session_state.hero_stack
    icm = st.session_state.icm_mode
    mode_name, mode_color = ("⚔️ PUSH/FOLD", "#ff4b4b") if stack <= 12 else (("🏆 ICM SURVIVAL", "#ffcc00") if icm else ("🟢 STANDARD GTO", "#28a745"))
    
    st.markdown(f"""
        <div style="background-color:{mode_color}; padding:8px; border-radius:8px; text-align:center; color:white; font-weight:bold; margin-bottom:10px;">
            모드: {mode_name}
        </div>
        <div style="background-color:#1e1e1e; padding:15px; border-radius:12px; border: 1px solid #444; margin-bottom:20px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <small style="color:#888;">MY HAND / BOARD</small><br>
                    <span style="font-size:18px; color:white;">🃏 {" ".join(st.session_state.hero_hand) if st.session_state.hero_hand else "?? ??"}</span>
                    <span style="margin-left:10px; color:#58a6ff;">{" ".join(st.session_state.board) if st.session_state.board else "---"}</span>
                </div>
                <div style="text-align:right;">
                    <small style="color:#888;">TOTAL POT / ODDS</small><br>
                    <span style="font-size:18px; color:#4caf50;">{current_pot:.1f} BB</span> | 
                    <span style="font-size:18px; color:#f44336;">{pot_odds:.1f}%</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# --- 4. 메인 단계 로직 ---

if st.session_state.step == 1:
    st.title("🏆 Tournament Advisor Setup")
    st.session_state.hero_stack = st.number_input("내 스택 (BB)", min_value=1.0, value=30.0)
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 10), value=9)
    pos_list = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"][:st.session_state.total]
    st.session_state.hero_pos = st.selectbox("나의 포지션", pos_list)
    st.session_state.icm_mode = st.toggle("ICM/버블 상황 활성화")
    if st.button("설정 완료 ➡️"): st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.title(f"🎮 {st.session_state.stage} Actions")
    
    # [정밀 팟 계산] 이전 누적 팟 + 현재 라운드 베팅
    current_round_bets = sum(st.session_state.villain_sizes.values()) + st.session_state.hero_bet_size
    current_total_pot = st.session_state.acc_pot + current_round_bets
    max_v_bet = max(st.session_state.villain_sizes.values()) if st.session_state.villain_sizes else 0
    to_call = max(0, max_v_bet - st.session_state.hero_bet_size)
    pot_odds = (to_call / (current_total_pot + to_call)) * 100 if to_call > 0 else 0
    
    display_dashboard(current_total_pot, pot_odds)
    
    pos_list = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"][:st.session_state.total]
    for p in pos_list:
        col1, col2, col3, col4 = st.columns([1, 1, 2, 1.5])
        if p == st.session_state.hero_pos:
            col1.warning("**HERO**")
            st.session_state.hero_action = col3.selectbox("내 액션", ["None", "Check", "Call", "Bet/Raise", "Fold"], key="h_act")
            if st.session_state.hero_action == "Bet/Raise":
                st.session_state.hero_bet_size = col4.number_input("BB 사이즈", min_value=0.0, step=0.5, key="h_sz")
            elif st.session_state.hero_action == "Call": st.session_state.hero_bet_size = max_v_bet
            else: st.session_state.hero_bet_size = 0.0
            continue
            
        is_f = p in st.session_state.folded
        col1.write(f"**{p}**")
        if col2.button("Fold", key=f"f_{p}", type="primary" if is_f else "secondary"):
            if is_f: st.session_state.folded.remove(p); st.session_state.villain_sizes.pop(p, None)
            else: st.session_state.folded.append(p); st.session_state.villain_sizes[p] = 0.0
            st.rerun()
            
        if not is_f:
            v_act = col3.selectbox("액션", ["None", "Check", "Call", "Bet/Raise", "All-in"], key=f"v_act_{p}")
            if v_act in ["Bet/Raise", "All-in"]:
                st.session_state.villain_sizes[p] = col4.number_input("BB", min_value=0.0, key=f"v_sz_{p}", step=0.5, value=st.session_state.villain_sizes.get(p, 0.0))
            else: st.session_state.villain_sizes[p] = 0.0

    if st.button("분석 및 카드 입력 ➡️"):
        st.session_state.acc_pot = current_total_pot # 현재 라운드 종료 시 팟 누적
        st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.title("📊 Strategic Report")
    
    # 분석 단계 대시보드
    max_v = max(st.session_state.villain_sizes.values()) if st.session_state.villain_sizes else 0
    to_call = max(0, max_v - st.session_state.hero_bet_size)
    p_odds = (to_call / (st.session_state.acc_pot + to_call)) * 100 if to_call > 0 else 0
    display_dashboard(st.session_state.acc_pot, p_odds)

    # [카드 피커]
    c1, c2 = st.columns(2)
    def card_picker(label, target_list, max_cnt):
        st.write(f"**{label}**")
        suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}; ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
        s_key = f"s_{label}"; scols = st.columns(4)
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

    if len(st.session_state.hero_hand) == 2:
        st.divider()
        equity = calculate_precise_stats(st.session_state.hero_hand, st.session_state.board)
        
        # [최종 특수 조언]
        spec_adv = get_advanced_special_advice(equity, p_odds, st.session_state.hero_stack, st.session_state.stage, st.session_state.hero_pos, st.session_state.hero_action, st.session_state.villain_sizes, st.session_state.icm_mode)
        
        st.subheader("🎯 AI 전략 가이드")
        res1, res2 = st.columns([1, 2])
        res1.metric("내 핸드 승률", f"{equity:.1f}%", delta=f"{equity-p_odds:.1f}% EV")
        with res2:
            for a in spec_adv: st.info(a)

        # 다음 단계 제어
        st.divider()
        cl, cr = st.columns(2)
        if cr.button("다음 라운드로 ➡️", disabled=st.session_state.stage == "River" or st.session_state.hero_action == "Fold"):
            st.session_state.stage = ["Pre-flop", "Flop", "Turn", "River"][["Pre-flop", "Flop", "Turn", "River"].index(st.session_state.stage)+1]
            st.session_state.villain_actions, st.session_state.villain_sizes = {}, {}
            st.session_state.hero_action, st.session_state.hero_bet_size = "None", 0.0
            st.session_state.step = 2; st.rerun()
        if cl.button("🔄 전체 리셋"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
