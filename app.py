import streamlit as st
import eval7

# --- 1. 정밀 계산 및 수학적 로직 ---
def calculate_precise_stats(hero_hand, board, iters=3000):
    try:
        if len(hero_hand) < 2: return 0.0, 0
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
        return (win_count / iters) * 100, 0
    except: return 0.0, 0

def get_m_ratio_advice(stack):
    m_ratio = stack / 1.5
    if m_ratio <= 5: return "🔴 레드 존: Push/Fold 전용 구간입니다. 콜은 최대한 지양하세요.", "red"
    elif m_ratio <= 10: return "🟠 오렌지 존: 공격적인 플레이가 필요합니다. 폴드 에퀴티를 활용하세요.", "orange"
    else: return "🟢 그린 존: 스택이 넉넉합니다. 표준 GTO 전략을 따르세요.", "green"

def sort_cards(card_list):
    rank_order = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
    return sorted(card_list, key=lambda x: rank_order.get(x[0], 0), reverse=True)

# --- 2. UI 세션 관리 ---
st.set_page_config(page_title="Tournament Strategy Pro", layout="centered")

if 'step' not in st.session_state:
    st.session_state.update({
        'step': 1, 'hero_hand': [], 'board': [], 'folded': [], 
        'villain_actions': {}, 'villain_sizes': {}, 'hero_action': "None",
        'stage': "Pre-flop", 'icm_mode': False, 'pushfold_mode': False, 
        'hero_pos': "BTN", 'total': 9, 'hero_stack': 30.0
    })

# --- 3. 카드 선택 컴포넌트 ---
def card_picker_final(label, target_list, max_count):
    st.write(f"**{label}**")
    suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}; ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    sel_key = f"suit_{label}"
    cols = st.columns(4)
    for i, (s_n, s_v) in enumerate(suits.items()):
        if cols[i].button(s_n, key=f"s_{label}_{s_v}", type="primary" if st.session_state.get(sel_key) == s_v else "secondary"):
            st.session_state[sel_key] = s_v; st.rerun()
    chosen_suit = st.session_state.get(sel_key)
    if chosen_suit:
        all_used = st.session_state.hero_hand + st.session_state.board
        for row in [ranks[:7], ranks[7:]]:
            r_cols = st.columns(7)
            for i, r in enumerate(row):
                card = f"{r}{chosen_suit}"
                is_sel = card in target_list
                if r_cols[i].button(r, key=f"r_{label}_{card}", disabled=card in all_used and not is_sel, type="primary" if is_sel else "secondary"):
                    if is_sel: target_list.remove(card)
                    elif len(target_list) < max_count: target_list.append(card)
                    st.rerun()

# --- 4. 메인 단계 ---

# [상단 고정 정보 바]
if st.session_state.step >= 3:
    h_s, b_s = sort_cards(st.session_state.hero_hand), sort_cards(st.session_state.board)
    st.info(f"🏟️ **{st.session_state.hero_pos}** | 스택: **{st.session_state.hero_stack}BB** | 단계: **{st.session_state.stage}** | {'ICM ON' if st.session_state.icm_mode else ''}")

# STEP 1: 설정
if st.session_state.step == 1:
    st.title("🏆 토너먼트 마스터 설정")
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 10), value=9)
    st.session_state.hero_stack = st.number_input("내 현재 스택 (BB)", min_value=1.0, value=30.0, step=1.0)
    pos_list = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"] if st.session_state.total > 6 else ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    st.session_state.hero_pos = st.selectbox("나의 포지션", pos_list[:st.session_state.total])
    c1, c2 = st.columns(2)
    st.session_state.icm_mode = c1.toggle("🏆 ICM (머니인 압박 반영)")
    st.session_state.pushfold_mode = c2.toggle("⚔️ Push/Fold 모드 강제")
    if st.button("설정 완료 ➡️"): st.session_state.step = 2; st.rerun()

# STEP 2: 상대 액션 입력
elif st.session_state.step == 2:
    st.title(f"🪑 2. {st.session_state.stage} 상대 액션")
    pos_list = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"] if st.session_state.total > 6 else ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    for p in pos_list[:st.session_state.total]:
        if p == st.session_state.hero_pos: continue
        col1, col2, col3, col4 = st.columns([1, 1, 2, 1.5])
        is_f = p in st.session_state.folded
        col1.write(f"**{p}**")
        if col2.button("Fold", key=f"f_{p}", type="primary" if is_f else "secondary"):
            if is_f: st.session_state.folded.remove(p); st.session_state.villain_sizes.pop(p, None)
            else: st.session_state.folded.append(p)
            st.rerun()
        if not is_f:
            act = col3.selectbox("Action", ["None", "Check", "Call", "Bet/Raise", "All-in"], key=f"act_{p}")
            st.session_state.villain_actions[p] = act
            if act in ["Bet/Raise", "All-in"]:
                st.session_state.villain_sizes[p] = col4.number_input("BB", min_value=0.0, key=f"sz_{p}", step=0.5)
            else: st.session_state.villain_sizes[p] = 0.0
            
    if st.button("카드 입력 이동 ➡️"): st.session_state.step = 3; st.rerun()

# STEP 3: 카드 입력
elif st.session_state.step == 3:
    st.title("🎴 3. 카드 및 보드 입력")
    if st.session_state.stage == "Pre-flop":
        card_picker_final("내 핸드 (2장)", st.session_state.hero_hand, 2)
    else:
        st.success(f"내 핸드: {' '.join(sort_cards(st.session_state.hero_hand))}")
    if st.session_state.stage != "Pre-flop":
        m_c = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 3)
        card_picker_final(f"보드 카드 ({m_c}장)", st.session_state.board, m_c)
    if len(st.session_state.hero_hand) == 2:
        if st.button("전략 분석 실행 ➡️", type="primary"): st.session_state.step = 4; st.rerun()

# STEP 4: 최종 분석 및 팟 오즈 조언
elif st.session_state.step == 4:
    st.title("🔍 실전 전략 분석")
    
    # [팟 크기 계산 로직]
    base_pot = 1.5 # Ante + Blinds 기본값
    villain_total_bet = sum(st.session_state.villain_sizes.values())
    current_pot = base_pot + villain_total_bet
    max_call_size = max(st.session_state.villain_sizes.values()) if st.session_state.villain_sizes else 0
    
    # 팟 오즈(필요 승률) 계산: Call / (Pot + Call)
    pot_odds = (max_call_size / (current_pot + max_call_size)) * 100 if max_call_size > 0 else 0

    # 상단 팟 오즈 대시보드
    st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:15px; border-radius:10px; border-left: 5px solid #00ff00; margin-bottom:20px;">
        <h4 style="margin:0; color:white;">💰 팟 정보 (Pot Odds)</h4>
        <span style="font-size:20px; color:#00ff00;">현재 팟: <b>{current_pot:.1f} BB</b></span> | 
        <span style="font-size:20px; color:#ff4b4b;">필요 승률: <b>{pot_odds:.1f}%</b></span>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner('정밀 시뮬레이션 중...'):
        equity, _ = calculate_precise_stats(st.session_state.hero_hand, st.session_state.board)
    
    # 지표 시각화
    c1, c2, c3 = st.columns(3)
    c1.metric("실제 승률 (Equity)", f"{equity:.1f}%")
    c2.metric("EV (기댓값)", "Positive" if equity > pot_odds else "Negative")
    c3.metric("M-Ratio", f"{st.session_state.hero_stack/1.5:.1f}")

    # [조언 섹션] - 매끄러운 조화
    st.subheader("💡 행동 지침")
    m_advice, m_color = get_m_ratio_advice(st.session_state.hero_stack)
    st.markdown(f"**스택 진단:** <span style='color:{m_color};'>{m_advice}</span>", unsafe_allow_html=True)

    if max_call_size > 0:
        if equity > pot_odds + (10 if st.session_state.icm_mode else 0):
            st.success(f"✅ **수학적 찬스**: 현재 팟 오즈({pot_odds:.1f}%) 대비 승률({equity:.1f}%)이 충분히 높습니다. **Call** 혹은 **Raise**가 수익적입니다.")
        else:
            st.error(f"❌ **수학적 손해**: 필요 승률보다 {pot_odds - equity:.1f}% 부족합니다. **Fold**를 권장합니다.")
    else:
        if equity > 60: st.success("🔥 **강력한 밸류**: 현재 매우 유리합니다. 벳을 통해 팟을 키우세요.")
        else: st.info("⚖️ **체크 권장**: 주도권이 없거나 마진 핸드입니다. 무료로 다음 카드를 보는 것이 좋습니다.")

    if st.session_state.icm_mode:
        st.warning("🏆 **ICM 모드 활성화**: 머니인 압박으로 인해 평소보다 더 타이트한 폴드 결정이 정답일 수 있습니다.")

    st.divider()
    # Hero Action & 단계 전환
    st.subheader("나의 액션 기록")
    h_cols = st.columns(4)
    for i, act in enumerate(["Check", "Call", "Bet/Raise", "Fold"]):
        if h_cols[i].button(act, key=f"h_{act}", type="primary" if st.session_state.hero_action == act else "secondary"):
            st.session_state.hero_action = act; st.rerun()

    col_l, col_r = st.columns(2)
    is_river = st.session_state.stage == "River"
    if col_r.button("다음 라운드로 ➡️", disabled=is_river or st.session_state.hero_action == "Fold"):
        stages = ["Pre-flop", "Flop", "Turn", "River"]
        st.session_state.stage = stages[stages.index(st.session_state.stage)+1]
        st.session_state.villain_actions, st.session_state.villain_sizes = {}, {}
        st.session_state.hero_action = "None"; st.session_state.step = 2; st.rerun()
    if col_l.button("🔄 게임 리셋"):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
