import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import os

# ──────────────────────────── 상수 ────────────────────────────
COMMISSION_RATE = 0.13
TAX_RATE = 0.033
APP_TITLE = "XAV 정산 자동화 프로그램 v2.0"

FILE_LABELS = {
    'delivery': '배송완료 리스트',
    'cancel': '취소관리 리스트',
    'return': '반품관리 리스트',
    'toss': '토스 정산내역',
}

REQUIRED_COLUMNS = {
    'delivery': ['주문번호', '주문상품명', '수령인 휴대전화', '주문자명'],
    'cancel': ['주문번호'],
    'return': ['주문번호'],
    'toss': ['주문번호', '결제·취소액 (A)'],
}

FILE_TYPES = [
    ("Excel/CSV 파일", "*.xlsx *.xls *.csv"),
    ("Excel 파일", "*.xlsx *.xls"),
    ("CSV 파일", "*.csv"),
    ("모든 파일", "*.*"),
]

HELP_TEXT = """사용 방법

1. 배송완료 리스트: 카페24에서 다운로드한 배송완료 주문 목록
   필수 컬럼: 주문번호, 주문상품명, 수령인 휴대전화, 주문자명, 옵션+판매가

2. 취소관리 리스트: 취소된 주문 목록
   필수 컬럼: 주문번호

3. 반품관리 리스트: 반품된 주문 목록
   필수 컬럼: 주문번호

4. 토스 정산내역: 토스페이먼츠 정산 데이터
   필수 컬럼: 주문번호, 결제·취소액 (A)

지원 파일 형식: .csv, .xlsx, .xls

정산 시작 버튼을 누르면 매출액, 수수료(13%), 세금(3.3%), 지급액이 자동 계산됩니다.
결과는 원하는 위치에 CSV 또는 Excel 파일로 저장할 수 있습니다."""


# ──────────────────────── 유틸리티 함수 ────────────────────────
def read_data_file(filepath):
    """확장자에 따라 CSV/XLSX/XLS 파일을 읽어 DataFrame으로 반환"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        return pd.read_csv(filepath, encoding='utf-8-sig')
    elif ext in ('.xlsx', '.xls'):
        return pd.read_excel(filepath)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}\n(.csv, .xlsx, .xls만 가능)")


def validate_columns(df, required_cols, file_label):
    """필수 컬럼 존재 여부 확인. 누락 시 ValueError 발생"""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        missing_str = ", ".join(f"'{c}'" for c in missing)
        raise ValueError(
            f"[{file_label}] 파일에 필수 컬럼이 없습니다.\n"
            f"누락된 컬럼: {missing_str}\n\n"
            f"필요한 컬럼: {', '.join(required_cols)}"
        )


# ──────────────────────── 메인 앱 클래스 ───────────────────────
class SettlementApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("620x380")
        self.root.minsize(550, 350)

        self.entries = {}
        self.status_labels = {}

        self._build_ui()

    def _build_ui(self):
        # 그리드 반응형 설정
        self.root.columnconfigure(1, weight=1)

        # 타이틀
        title_label = tk.Label(
            self.root, text=APP_TITLE,
            font=("맑은 고딕", 14, "bold"), pady=10
        )
        title_label.grid(row=0, column=0, columnspan=4, sticky='ew')

        # 파일 입력 행 생성
        keys = list(FILE_LABELS.keys())
        for idx, key in enumerate(keys):
            row = idx + 1
            label_text = FILE_LABELS[key] + ':'

            tk.Label(self.root, text=label_text, font=("맑은 고딕", 9)).grid(
                row=row, column=0, padx=(15, 5), pady=8, sticky='w'
            )

            entry = tk.Entry(self.root, width=40, font=("맑은 고딕", 9))
            entry.grid(row=row, column=1, padx=5, pady=8, sticky='ew')
            self.entries[key] = entry

            tk.Button(
                self.root, text="파일 찾기", font=("맑은 고딕", 8),
                command=lambda k=key: self._select_file(k)
            ).grid(row=row, column=2, padx=5, pady=8)

            status_lbl = tk.Label(self.root, text="", width=3, font=("맑은 고딕", 10))
            status_lbl.grid(row=row, column=3, padx=(0, 10), pady=8)
            self.status_labels[key] = status_lbl

        # 하단 버튼 프레임
        btn_frame = tk.Frame(self.root)
        btn_frame.grid(row=len(keys) + 1, column=0, columnspan=4, pady=20)

        tk.Button(
            btn_frame, text=" ? 사용법 ", font=("맑은 고딕", 10),
            command=self._show_help, relief="groove"
        ).pack(side='left', padx=15)

        tk.Button(
            btn_frame, text="  정산 시작!  ", font=("맑은 고딕", 12, "bold"),
            command=self._process, bg="black", fg="white",
            activebackground="#333333", activeforeground="white"
        ).pack(side='left', padx=15)

    def _select_file(self, key):
        """파일 선택 다이얼로그 + 즉시 검증"""
        filepath = filedialog.askopenfilename(filetypes=FILE_TYPES)
        if not filepath:
            return

        entry = self.entries[key]
        entry.delete(0, tk.END)
        entry.insert(0, filepath)

        # 즉시 검증
        status_lbl = self.status_labels[key]
        try:
            df = read_data_file(filepath)
            validate_columns(df, REQUIRED_COLUMNS[key], FILE_LABELS[key])
            status_lbl.config(text="O", fg="green")
        except Exception as e:
            status_lbl.config(text="X", fg="red")
            messagebox.showwarning(
                "파일 검증 실패",
                f"{FILE_LABELS[key]} 파일에 문제가 있습니다.\n\n{str(e)}"
            )

    def _show_help(self):
        """사용법 안내 팝업"""
        help_win = tk.Toplevel(self.root)
        help_win.title("사용법 안내")
        help_win.geometry("500x400")
        help_win.resizable(False, False)

        text_widget = tk.Text(
            help_win, wrap='word', padx=15, pady=15,
            font=("맑은 고딕", 10), relief='flat'
        )
        text_widget.insert('1.0', HELP_TEXT)
        text_widget.config(state='disabled')
        text_widget.pack(fill='both', expand=True)

        tk.Button(
            help_win, text="닫기", command=help_win.destroy,
            font=("맑은 고딕", 10)
        ).pack(pady=10)

    def _process(self):
        """정산 처리 메인 로직"""
        # 1. 파일 경로 입력 확인
        missing_files = [
            FILE_LABELS[k] for k, e in self.entries.items() if not e.get().strip()
        ]
        if missing_files:
            messagebox.showwarning(
                "파일 미선택",
                f"다음 파일을 선택해주세요:\n\n" + "\n".join(f"- {f}" for f in missing_files)
            )
            return

        # 2. 파일 존재 여부 확인
        for key, entry in self.entries.items():
            path = entry.get().strip()
            if not os.path.isfile(path):
                messagebox.showerror(
                    "파일 없음",
                    f"[{FILE_LABELS[key]}] 파일을 찾을 수 없습니다:\n{path}"
                )
                return

        # 대기 커서 설정
        self.root.config(cursor="wait")
        self.root.update()

        try:
            # 3. 파일 읽기
            dfs = {}
            for key, entry in self.entries.items():
                try:
                    dfs[key] = read_data_file(entry.get().strip())
                except Exception as e:
                    messagebox.showerror(
                        "파일 읽기 실패",
                        f"[{FILE_LABELS[key]}] 파일을 읽을 수 없습니다.\n\n{str(e)}"
                    )
                    return

            # 4. 컬럼 검증
            for key, df in dfs.items():
                try:
                    validate_columns(df, REQUIRED_COLUMNS[key], FILE_LABELS[key])
                except ValueError as e:
                    messagebox.showerror("컬럼 오류", str(e))
                    return

            df_delivery = dfs['delivery']
            df_cancel = dfs['cancel']
            df_return = dfs['return']
            df_toss = dfs['toss']

            # 5. 취소/반품 주문번호 세트
            cancel_set = set(df_cancel['주문번호'])
            return_set = set(df_return['주문번호'])

            # 토스 정산 금액 (주문번호별 합계)
            toss_grouped = df_toss.groupby('주문번호')['결제·취소액 (A)'].sum().reset_index()
            toss_dict = dict(zip(toss_grouped['주문번호'], toss_grouped['결제·취소액 (A)']))

            # 6. 결과 DataFrame 생성
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

            # 7. 요약 계산
            total_sales = df_final['총 실결제금액'].sum()
            commission = int(total_sales * COMMISSION_RATE)
            tax = int(commission * TAX_RATE)
            payout = commission - tax

            # 구분 행 + 요약 행 추가
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
            df_final = pd.concat([df_final, pd.DataFrame(summary_rows)], ignore_index=True)

            # 8. 저장 위치 선택
            desktop = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), 'Desktop')
            if not os.path.isdir(desktop):
                desktop = os.path.expanduser('~')

            save_path = filedialog.asksaveasfilename(
                title="정산 보고서 저장",
                defaultextension=".xlsx",
                filetypes=[("Excel 파일", "*.xlsx"), ("CSV 파일", "*.csv")],
                initialfile="최종_정산보고서",
                initialdir=desktop,
            )
            if not save_path:
                return

            # 9. 파일 저장
            ext = os.path.splitext(save_path)[1].lower()
            if ext == '.csv':
                df_final.to_csv(save_path, index=False, encoding='utf-8-sig')
            else:
                df_final.to_excel(save_path, index=False, sheet_name='정산결과')

            # 10. 성공 메시지
            messagebox.showinfo(
                "정산 완료!",
                f"정산 보고서가 저장되었습니다.\n\n"
                f"저장 위치: {save_path}\n\n"
                f"─── 요약 ───\n"
                f"총 매출액: {total_sales:,.0f}원\n"
                f"수수료({int(COMMISSION_RATE * 100)}%): {commission:,.0f}원\n"
                f"세금({TAX_RATE * 100:.1f}%): {tax:,.0f}원\n"
                f"지급액: {payout:,.0f}원"
            )

        except PermissionError:
            messagebox.showerror(
                "저장 실패",
                "파일을 저장할 수 없습니다.\n"
                "해당 파일이 다른 프로그램에서 열려 있는지 확인해주세요."
            )
        except Exception as e:
            messagebox.showerror("에러 발생", f"문제가 생겼습니다:\n{str(e)}")
        finally:
            self.root.config(cursor="")


# ──────────────────────── 프로그램 시작 ────────────────────────
if __name__ == '__main__':
    root = tk.Tk()
    app = SettlementApp(root)
    root.mainloop()
