import gradio as gr
import pandas as pd
import os
import tempfile

# ──────────────────────────── 상수 ────────────────────────────
COMMISSION_RATE = 0.13
TAX_RATE = 0.033

REQUIRED_COLUMNS = {
    'delivery': ['주문번호', '주문상품명', '수령인 휴대전화', '주문자명'],
    'cancel': ['주문번호'],
    'return': ['주문번호'],
    'toss': ['주문번호', '결제·취소액 (A)'],
}

FILE_LABELS = {
    'delivery': '배송완료 리스트',
    'cancel': '취소관리 리스트',
    'return': '반품관리 리스트',
    'toss': '토스 정산내역',
}


# ──────────────────────── 유틸리티 함수 ────────────────────────
def read_data_file(filepath):
    """확장자에 따라 CSV/XLSX/XLS 파일을 읽어 DataFrame으로 반환"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath, encoding='utf-8-sig')
    elif ext in ('.xlsx', '.xls'):
        return pd.read_excel(filepath)
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {ext} (.csv, .xlsx, .xls만 가능)")


def validate_columns(df, required_cols, file_label):
    """필수 컬럼 존재 여부 확인"""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        missing_str = ", ".join(f"'{c}'" for c in missing)
        raise ValueError(
            f"[{file_label}] 필수 컬럼 누락: {missing_str}\n"
            f"필요한 컬럼: {', '.join(required_cols)}"
        )


# ──────────────────────── 정산 처리 함수 ───────────────────────
def process_settlement(delivery_file, cancel_file, return_file, toss_file):
    """정산 처리 메인 로직. Gradio에서 호출됨."""

    # 1. 파일 입력 확인
    files = {
        'delivery': delivery_file,
        'cancel': cancel_file,
        'return': return_file,
        'toss': toss_file,
    }

    missing = [FILE_LABELS[k] for k, v in files.items() if v is None]
    if missing:
        raise gr.Error(f"파일을 선택해주세요: {', '.join(missing)}")

    # 2. 파일 읽기 + 컬럼 검증
    dfs = {}
    for key, file in files.items():
        filepath = file.name if hasattr(file, 'name') else file
        try:
            dfs[key] = read_data_file(filepath)
        except Exception as e:
            raise gr.Error(f"[{FILE_LABELS[key]}] 파일 읽기 실패:\n{str(e)}")

        try:
            validate_columns(dfs[key], REQUIRED_COLUMNS[key], FILE_LABELS[key])
        except ValueError as e:
            raise gr.Error(str(e))

    df_delivery = dfs['delivery']
    df_cancel = dfs['cancel']
    df_return = dfs['return']
    df_toss = dfs['toss']

    # 3. 취소/반품 주문번호 세트
    cancel_set = set(df_cancel['주문번호'])
    return_set = set(df_return['주문번호'])

    # 토스 정산 금액 (주문번호별 합계)
    toss_grouped = df_toss.groupby('주문번호')['결제·취소액 (A)'].sum().reset_index()
    toss_dict = dict(zip(toss_grouped['주문번호'], toss_grouped['결제·취소액 (A)']))

    # 4. 결과 데이터 생성
    data = []
    for _, row in df_delivery.iterrows():
        order_no = row['주문번호']

        if order_no in return_set:
            status, amount = '반품', 0
        elif order_no in cancel_set:
            status, amount = '취소', 0
        else:
            status = '취소안함'
            amount = toss_dict.get(order_no, row.get('옵션+판매가', 0))

        data.append({
            '주문번호': order_no,
            '주문상품명(옵션포함)': row['주문상품명'],
            '수령인 휴대전화': row['수령인 휴대전화'],
            '주문자명': row['주문자명'],
            '취소구분': status,
            '수량': 1,
            '총 실결제금액': amount,
        })

    df_final = pd.DataFrame(data)

    # 5. 요약 계산
    total_sales = df_final['총 실결제금액'].sum()
    commission = int(total_sales * COMMISSION_RATE)
    tax = int(commission * TAX_RATE)
    payout = commission - tax

    # 요약 텍스트
    summary = (
        f"## 정산 결과\n\n"
        f"| 항목 | 금액 |\n"
        f"|------|------|\n"
        f"| 총 주문 건수 | {len(df_final)}건 |\n"
        f"| 취소 | {len(df_final[df_final['취소구분'] == '취소'])}건 |\n"
        f"| 반품 | {len(df_final[df_final['취소구분'] == '반품'])}건 |\n"
        f"| **총 매출액** | **{total_sales:,.0f}원** |\n"
        f"| 수수료({int(COMMISSION_RATE * 100)}%) | {commission:,.0f}원 |\n"
        f"| 세금({TAX_RATE * 100:.1f}%) | {tax:,.0f}원 |\n"
        f"| **지급액** | **{payout:,.0f}원** |\n"
    )

    # 6. 구분 행 + 요약 행 추가한 최종 DataFrame
    separator = {col: '' for col in df_final.columns}
    separator['주문번호'] = '───'
    separator['주문자명'] = '── 요약 ──'

    summary_rows = [
        separator,
        {'주문번호': '', '주문자명': '매출액', '총 실결제금액': total_sales},
        {'주문번호': '', '주문자명': f'수수료({int(COMMISSION_RATE * 100)}%)', '총 실결제금액': commission},
        {'주문번호': '', '주문자명': f'세금({TAX_RATE * 100:.1f}%)', '총 실결제금액': tax},
        {'주문번호': '', '주문자명': '지급액', '총 실결제금액': payout},
    ]
    df_export = pd.concat([df_final, pd.DataFrame(summary_rows)], ignore_index=True)

    # 7. 다운로드용 파일 생성 (xlsx + csv)
    xlsx_path = os.path.join(tempfile.gettempdir(), '최종_정산보고서.xlsx')
    csv_path = os.path.join(tempfile.gettempdir(), '최종_정산보고서.csv')
    df_export.to_excel(xlsx_path, index=False, sheet_name='정산결과')
    df_export.to_csv(csv_path, index=False, encoding='utf-8-sig')

    return summary, df_final, xlsx_path, csv_path


# ──────────────────────── Gradio UI ────────────────────────
HELP_TEXT = """
### 사용 방법

1. **배송완료 리스트**: 카페24에서 다운로드한 배송완료 주문 목록
   - 필수 컬럼: `주문번호`, `주문상품명`, `수령인 휴대전화`, `주문자명`, `옵션+판매가`

2. **취소관리 리스트**: 취소된 주문 목록
   - 필수 컬럼: `주문번호`

3. **반품관리 리스트**: 반품된 주문 목록
   - 필수 컬럼: `주문번호`

4. **토스 정산내역**: 토스페이먼츠 정산 데이터
   - 필수 컬럼: `주문번호`, `결제·취소액 (A)`

**지원 파일**: `.csv`, `.xlsx`, `.xls`
"""

with gr.Blocks(title="XAV 정산 자동화") as app:
    gr.Markdown("# XAV 정산 자동화 프로그램 v2.0")

    with gr.Accordion("사용법 안내", open=False):
        gr.Markdown(HELP_TEXT)

    with gr.Row():
        with gr.Column():
            delivery_input = gr.File(label="배송완료 리스트", file_types=[".csv", ".xlsx", ".xls"])
            cancel_input = gr.File(label="취소관리 리스트", file_types=[".csv", ".xlsx", ".xls"])
        with gr.Column():
            return_input = gr.File(label="반품관리 리스트", file_types=[".csv", ".xlsx", ".xls"])
            toss_input = gr.File(label="토스 정산내역", file_types=[".csv", ".xlsx", ".xls"])

    process_btn = gr.Button("정산 시작!", variant="primary", size="lg")

    summary_output = gr.Markdown(label="정산 요약")
    detail_table = gr.Dataframe(label="상세 내역", interactive=False)

    with gr.Row():
        xlsx_download = gr.File(label="Excel 다운로드")
        csv_download = gr.File(label="CSV 다운로드")

    process_btn.click(
        fn=process_settlement,
        inputs=[delivery_input, cancel_input, return_input, toss_input],
        outputs=[summary_output, detail_table, xlsx_download, csv_download],
    )

if __name__ == '__main__':
    app.launch(theme=gr.themes.Soft(), share=True)
