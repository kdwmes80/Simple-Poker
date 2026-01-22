import streamlit as st
import eval7

# --- 1. 유틸리티 함수 (엄격한 정렬 로직) ---
def calculate_poker_stats(hero_hand, board):
    try:
        hero_c = [eval7.Card(c) for c in hero_hand]
        board_c = [eval7.Card(c) for c in board]
        win_count, iters = 0, 1000 
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
        
        equity = (win_count / iters) * 100
        outs = 0
        if len(board_c) < 5:
            current_score = eval7.evaluate(hero_c + board_c)
            deck = eval7.Deck()
            for c in hero_c + board_c:
                if c in deck.cards: deck.cards.remove(c)
            for c in deck.cards:
                if eval7.evaluate(hero_c + board_c + [c]) > current_score:
                    outs += 1
        return equity, outs
    except: return 0, 0

# 카드 내림차순 정렬 (A > K > Q ... > 2)
def sort_cards(card_list):
    if not card_list: return []
    rank_order = {'A':14, 'K':13, 'Q':12, 'J':11, 'T':10, '9':9, '8':8, '7':7, '6':6, '5':5, '4':4, '3':3, '2':2}
    return sorted(card_list, key=lambda x: rank_order.get(x[0], 0), reverse=True)

# --- 2. UI 스타일 (폴드 시 회색 처리 및 레이아웃 강제) ---
st.set_page_config(page_title="Poker Pro Master", layout="centered")

st.markdown("""
    <style>
    /* 전체 버튼 높이 조절 */
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3.5em; }
    
    /* 폴드(비활성화) 스타일: 투명도와 회색 필터 강제 적용 */
    .folded-box { 
        opacity: 0.3 !important; 
        filter: grayscale(100%) !important; 
        pointer-events: none; 
        border: 1px solid #444;
        padding: 5px;
        border-radius: 10px;
    }
    
    /* 활성 플레이어 박스 */
    .active-box {
        border: 1px solid #3498db;
        padding: 5px;
        border-radius: 10px;
        margin-bottom: 5px;
    }

    /* 상단 상태 바 */
    .status-bar { 
        background-color: #1e2129; padding: 15px; border-radius: 10px; 
        border-bottom: 3px solid #3498db; margin-bottom: 20px; position: sticky; top: 0; z-index: 999;
    }
    .card-tag { background: #34495e; padding: 4px 10px; border-radius: 4px; margin-right: 5px; color: #fff; font-family: 'Courier New', Courier, monospace; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화
if 'step' not in st.session_state: st.session_state.step = 1
if 'folded' not in st.session_state: st.session_state.folded = []
if 'dealer' not in st.session_state: st.session_state.dealer = None
if 'hero_hand' not in st.session_state: st.session_state.hero_hand = []
if 'board' not in st.session_state: st.session_state.board = []
if 'stage' not in st.session_state: st.session_state.stage = "Pre-flop"
if 'last_action' not in st.session_state: st.session_state.last_action = "None"
if 'icm_mode' not in st.session_state: st.session_state.icm_mode = False
if 'pushfold_mode' not in st.session_state: st.session_state.pushfold_mode = False

# --- 3. 상단 상태바 (카드 정렬 및 정보 상시 노출) ---
if st.session_state.step >= 3:
    h_s = sort_cards(st.session_state.hero_hand)
    b_s = sort_cards(st.session_state.board)
    st.markdown(f"""
        <div class="status-bar">
            <small style="color:#bbb;">MY HAND</small><br>
            {" ".join([f"<span class='card-tag'>{c}</span>" for c in h_s]) if h_s else "<span style='color:#555;'>Empty</span>"}<br>
            <small style="color:#bbb; margin-top:5px; display:inline-block;">BOARD</small><br>
            {" ".join([f"<span class='card-tag'>{c}</span>" for c in b_s]) if b_s else "<span style='color:#555;'>Empty</span>"}
        </div>
    """, unsafe_allow_html=True)

# --- 4. 카드 선택 컴포넌트 (그리드 레이아웃 고정) ---
def card_picker(label, target_list, max_count):
    st.write(f"### {label}")
    suits = {'♠':'s', '♥':'h', '◆':'d', '♣':'c'}
    ranks = ['A','K','Q','J','T','9','8','7','6','5','4','3','2']
    
    # 문양 선택 (가로 4칸)
    sel_key = f"suit_{label}"
    suit_cols = st.columns(4)
    for i, (s_name, s_val) in enumerate(suits.items()):
        if suit_cols[i].button(s_name, key=f"sbtn_{label}_{s_val}", 
                               type="primary" if st.session_state.get(sel_key) == s_val else "secondary"):
            st.session_state[sel_key] = s_val
            st.rerun()

    # 숫자 선택 (가로 7칸 그리드 강제)
    chosen_suit = st.session_state.get(sel_key)
    if chosen_suit:
        st.write(f"**{chosen_suit.upper()}** 문양 숫자 선택:")
        all_used = st.session_state.hero_hand + st.session_state.board
        
        # 14개 숫자를 7열씩 2줄로 배치
        for row in [ranks[:7], ranks[7:]]:
            cols = st.columns(7)
            for idx, r in enumerate(row):
                card_code = f"{r}{chosen_suit}"
                is_selected = card_code in target_list
                is_disabled = card_code in all_used and not is_selected
                
                if cols[idx].button(r, key=f"rbtn_{label}_{card_code}", 
                                    disabled=is_disabled,
                                    type="primary" if is_selected else "secondary"):
                    if is_selected: target_list.remove(card_code)
                    elif len(target_list) < max_count: target_list.append(card_code)
                    st.rerun()

# --- 5. 단계별 실행 ---

# [STEP 1] 인원 및 모드 설정
if st.session_state.step == 1:
    st.title("🏟️ 1. 환경 설정")
    st.session_state.total = st.select_slider("테이블 인원", options=range(2, 11), value=9)
    c1, c2 = st.columns(2)
    with c1: st.session_state.icm_mode = st.toggle("🏆 ICM 분석 모드")
    with c2: st.session_state.pushfold_mode = st.toggle("⚔️ Push/Fold 모드")
    if st.button("테이블 생성 ➡️"): st.session_state.step = 2; st.rerun()

# [STEP 2] 테이블 배치 및 폴드/딜러 설정
elif st.session_state.step == 2:
    st.title("🪑 2. 테이블 배치")
    st.info("P0은 Hero(나)입니다. 딜러를 정하고 폴드된 인원을 체크하세요.")
    
    for i in range(0, st.session_state.total, 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < st.session_state.total:
                with cols[j]:
                    is_f = idx in st.session_state.folded
                    is_d = st.session_state.dealer == idx
                    
                    # 폴드 상태에 따라 클래스 분기
                    box_class = "folded-box" if is_f else "active-box"
                    st.markdown(f"<div class='{box_class}'>", unsafe_allow_html=True)
                    st.write(f"**{'P0 (Hero)' if idx == 0 else f'P{idx}'}**")
                    
                    d_btn_label = "Dealer" if is_d else "D"
                    if st.button(d_btn_label, key=f"d{idx}", disabled=is_f, type="primary" if is_d else "secondary"):
                        st.session_state.dealer = idx
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

                    if idx != 0: # Hero는 폴드 버튼 없음
                        if st.button("Fold" if not is_f else "Unfold", key=f"f{idx}"):
                            if is_f: st.session_state.folded.remove(idx)
                            else: 
                                st.session_state.folded.append(idx)
                                if st.session_state.dealer == idx: st.session_state.dealer = None
                            st.rerun()

    if st.session_state.dealer is not None:
        if st.button("다음: 카드 선택 ➡️", type="primary"): st.session_state.step = 3; st.rerun()

# [STEP 3] 내 핸드 선택
elif st.session_state.step == 3:
    st.title("🎴 3. 내 핸드 선택")
    card_picker("My Hand (2장)", st.session_state.hero_hand, 2)
    if len(st.session_state.hero_hand) == 2:
        if st.button("분석 시작 ➡️", type="primary"): st.session_state.step = 4; st.rerun()

# [STEP 4] 보드 및 액션 분석
elif st.session_state.step == 4:
    st.title(f"📊 {st.session_state.stage}")
    if st.session_state.stage != "Pre-flop":
        m_count = {'Flop':3, 'Turn':4, 'River':5}.get(st.session_state.stage, 5)
        card_picker("Board Cards", st.session_state.board, m_count)

    st.divider()
    st.subheader("상대방 액션")
    act_list = ["Check", "Call", "Bet", "Raise", "All-in"]
    act_cols = st.columns(5)
    for i, act in enumerate(act_list):
        if act_cols[i].button(act, key=f"act_{act}", type="primary" if st.session_state.last_action == act else "secondary"):
            st.session_state.last_action = act
            st.rerun()

    if st.button("🔍 데이터 분석 실행", use_container_width=True):
        eq, outs = calculate_poker_stats(st.session_state.hero_hand, st.session_state.board)
        c1, c2 = st.columns(2)
        c1.metric("승률 (Equity)", f"{eq:.1f}%")
        c2.metric("아우츠 (Outs)", f"{outs}개")
        
        if eq >= 70: st.success("🔥 승률이 매우 높습니다! 공격적으로 플레이하세요.")
        elif eq >= 45: st.warning("⚖️ 마진 상황입니다. 팟 오즈를 고려하세요.")
        else: st.error("❌ 현재 불리합니다. 폴드를 진지하게 고려하세요.")

    st.divider()
    stages = ["Pre-flop", "Flop", "Turn", "River", "End"]
    curr_idx = stages.index(st.session_state.stage)
    
    col_prev, col_next = st.columns(2)
    if st.session_state.stage != "End":
        if col_next.button("다음 단계로 ➡️"):
            st.session_state.stage = stages[curr_idx+1]
            st.rerun()
    else:
        if st.button("🔄 전체 세션 초기화", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()
    
    if col_prev.button("⬅️ 테이블 수정"):
        st.session_state.step = 2
        st.rerun()
