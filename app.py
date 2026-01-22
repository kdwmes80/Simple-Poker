import streamlit as st
import eval7

# --- 1. 정밀 계산 및 분석 로직 ---
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
    except:
        return 0.0, 0

def get_m_ratio_advice(stack):
    m_ratio = stack / 1.5 # Ante 미포함 간소화 계산
    if m_ratio <= 5: return "🔴 레드 존: Push/Fold 전용. 모든 핸드를 올인 혹은 폴드로만 결정하세요.", "red"
    elif m_ratio <= 10: return "🟠 오렌지 존: 매우 공격적인 레이즈가 필요합니다. 주도권을 뺏기지 마세요.", "orange"
    else: return "🟢 그린 존: 스택 여유가 있습니다. 표준 GTO 레인지를 활용하세요.", "green"

def sort_cards(card_list):
    rank_order = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
    return sorted(card_list, key=lambda x: rank_order.get(x[0], 0), reverse=True)

# --- 2. UI 세션 관리 (누락 방지) ---
st.set_page_config(page_title="Tournament Strategy Pro", layout="centered")

if 'step' not in st.session_state:
    st.session_state.update({
        'step': 1, 'hero_hand': [], 'board': [], 'folded': [], 
        'villain_actions': {}, 'villain_sizes': {}, 'hero_action': "None",
        'stage': "Pre-flop", 'icm_mode': False, 'pushfold_mode': False, 
        'hero_pos': "BTN", 'total': 9, 'hero_stack': 30.0
    })

# --- 3. 통합 정보 대시보드 ---
def display_integrated_dashboard(current_pot, pot_odds):
    h_s = sort_cards(st.session_state.hero_hand)
    b_s = sort_cards(st.session_state.board)
    
    st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:15px; border-radius:10px; border-left: 5px solid #00ff00; margin-bottom:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <small style="color:#888;">MY HAND & BOARD</small><br>
                <span style="font-size:20px; color:#ffffff;">🃏 <b>{" ".join(h_s) if h_s else "?? ??"}</b></span>
                <span style="margin-left:15px; font-size:18px; color:#aaa;">🖥️ {" ".join(b_s) if b_s else "---"}</span>
            </div>
            <div style="text-align:right;">
                <small style="color:#888;">POT & ODDS</small><br>
                <span style="font-size:20px; color:#00ff00;">💰 <b>{current_pot:.1f} BB</b></span> | 
                <span style="font-size:20px; color:#ff4b4b;">🎯 <b>{pot_odds:.1f}%</b></span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- 4. 단계별 실행 로직 ---

# STEP 1: 토너먼트 환경 설정
if st.session_state.step == 1:
    st.title("🏆 Tournament Master Setup")
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 10), value=9)
    st.session_state.hero_stack = st.number_input("내 현재 스택 (BB)", min_value=1.0, value=30.0, step=1.0)
    
    pos_list = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"] if st.session_state.total > 6 else ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    st.session_state.hero_pos = st.selectbox("나의 포지션", pos_list[:st.session_state.total])
    
    c1, c2 = st.columns(2)
    st.session_state.icm_mode = c1.toggle("ICM 압박 (머니인/버블)")
    st.session_state.pushfold_mode = c2.toggle("Push/Fold 가이드 강제")
    
    if st.button("설정 완료 ➡️"): st.session_state.step = 2; st.rerun()

# STEP 2: 액션 입력 (상대 + 나)
elif st.session_state.step == 2:
    st.title(f"🎮 {st.session_state.stage}: Action")
    
    current_pot = 1.5 + sum(st.session_state.villain_sizes.values())
    max_bet = max(st.session_state.villain_sizes.values()) if st.session_state.villain_sizes else 0
    pot_odds = (max_bet / (current_pot + max_bet)) * 100 if max_bet > 0 else 0
    
    display_integrated_dashboard(current_pot, pot_odds)
    
    pos_list = ["UTG", "UTG+1", "UTG+2", "LJ", "HJ", "CO", "BTN", "SB", "BB"] if st.session_state.total > 6 else ["UTG", "HJ", "CO", "BTN", "SB", "BB"]
    
    for p in pos_list[:st.session_state.total]:
        col1, col2, col3, col4 = st.columns([1, 1, 2, 1.5])
        
        if p == st.session_state.hero_pos:
            col1.warning("**HERO**")
            st.session_state.hero_action = col3.selectbox("나의 결정", ["None", "Check", "Call", "Bet/Raise", "Fold"], key="hero_act_input")
            continue
            
        is_f = p in st.session_state.folded
        col1.write(f"**{p}**")
        if col2.button("Fold", key=f"f_{p}", type="primary" if is_f else "secondary"):
            if is_f: st.session_state.folded.remove(p); st.session_state.villain_sizes.pop(p, None)
            else: 
                st.session_state.folded.append(p)
                st.session_state.villain_sizes[p] = 0.0
            st.rerun()
            
        if not is_f:
            act = col3.selectbox("액션", ["None", "Check", "Call", "Bet/Raise", "All-in"], key=f"act_{p}")
            st.session_state.villain_actions[p] = act
            if act in ["Bet/Raise", "All-in"]:
                st.session_state.villain_sizes[p] = col4.number_input("BB", min_value=0.0, key=f"sz_{p}", step=0.5, value=st.session_state.villain_sizes.get(p, 0.0))
            else:
                st.session_state.villain_sizes[p] = 0.0
            
    if st.button("카드 입력 및 결과 분석 ➡️"): st.session_state.step = 3; st.rerun()

# STEP 3: 카드 입력 (최종 분석 포함)
elif st.session_state.step == 3:
    st.title("🔍 카드 입력 및 분석")
    
    current_pot = 1.5 + sum(st.session_state.villain_sizes.values())
    max_bet = max(st.session_state.villain_sizes.values()) if st.session_state.villain_sizes else 0
    pot_odds = (max_bet / (current_pot + max_bet)) * 100 if max_bet > 0 else 0
    display_integrated_dashboard(current_pot, pot_odds)

    # 카드 피커 로직
    def card_picker(label, target_list, max_cnt):
        st.write(f"**{label}**")
        suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}; ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
        s_key = f"s_{label}"; cols = st.columns(4)
        for i, (sn, sv) in enumerate(suits.items()):
            if cols[i].button(sn, key=f"{s_key}_{sv}", type="primary" if st.session_state.get(s_key) == sv else "secondary"):
                st.session_state[s_key] = sv; st.rerun()
        chosen_s = st.session_state.get(s_key)
        if chosen_s:
            all_u = st.session_state.hero_hand + st.session_state.board
            for row in [ranks[:7], ranks[7:]]:
                r_cols = st.columns(7)
                for i, r in enumerate(row):
                    card = f"{r}{chosen_s}"
                    is_s = card in target_list
                    if r_cols[i].button(r, key=f"r_{label}_{card}", disabled=card in all_u and not is_s, type="primary" if is_s else "secondary"):
                        if is_s: target_list.remove(card)
                        elif len(target_list) < max_cnt: target_list.append(card)
                        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        if st.session_state.stage == "Pre-flop": card_picker("내 핸드", st.session_state.hero_hand, 2)
        else: st.success(f"내 핸드 고정됨: {' '.join(sort_cards(st.session_state.hero_hand))}")
    with c2:
        if st.session_state.stage != "Pre-flop":
            m_c = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 3)
            card_picker(f"보드 ({st.session_state.stage})", st.session_state.board, m_c)

    if len(st.session_state.hero_hand) == 2:
        st.divider()
        with st.spinner('정밀 승률 분석 중...'):
            equity, _ = calculate_precise_stats(st.session_state.hero_hand, st.session_state.board)
        
        m_adv, m_col = get_m_ratio_advice(st.session_state.hero_stack)
        st.markdown(f"**📍 스택 진단**: <span style='color:{m_col};'>{m_adv}</span>", unsafe_allow_html=True)
        
        res1, res2 = st.columns(2)
        res1.metric("실제 승률 (Equity)", f"{equity:.1f}%")
        res2.metric("필요 승률 (Pot Odds)", f"{pot_odds:.1f}%")

        # 최종 가이드
        icm_adj = 7.0 if st.session_state.icm_mode else 0.0
        if max_bet > 0:
            if equity > pot_odds + icm_adj: st.success("✅ **추천: Call/Raise** - 수학적으로 유리한 구간입니다.")
            else: st.error("❌ **추천: Fold** - 기대값이 낮습니다.")
        
        # 다음 단계 제어
        st.divider()
        col_l, col_r = st.columns(2)
        is_river = st.session_state.stage == "River"
        if col_r.button("다음 라운드로 ➡️", disabled=is_river or st.session_state.hero_action == "Fold"):
            stages = ["Pre-flop", "Flop", "Turn", "River"]
            st.session_state.stage = stages[stages.index(st.session_state.stage)+1]
            st.session_state.villain_actions, st.session_state.villain_sizes = {}, {}
            st.session_state.hero_action = "None"; st.session_state.step = 2; st.rerun()
        if col_l.button("🔄 리셋"):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
