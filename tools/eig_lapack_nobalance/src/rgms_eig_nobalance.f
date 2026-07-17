*> RGMs Option B — C ABI wrapper around LAPACK DGEEVX (BALANC='N').
*> Matches MATLAB eig(A,'nobalance') contract used by eig_nobalance.py.
      SUBROUTINE rgms_eig_nobalance_dgeevx(
     $     N, A, LDA, WR, WI, VR, LDVR, INFO)
     $     BIND(C, NAME='rgms_eig_nobalance_dgeevx')
      INTEGER N, LDA, LDVR, INFO
      DOUBLE PRECISION A(LDA,*), WR(*), WI(*), VR(LDVR,*)
      CHARACTER BALANC, JOBVL, JOBVR, SENSE
      PARAMETER (BALANC='N', JOBVL='N', JOBVR='V', SENSE='N')
      INTEGER ILO, IHI, LWORK, LIWORK, IERR
      DOUBLE PRECISION ABNRM, DUMVL(1,1), DUMRC(1), DUMRV(1)
      DOUBLE PRECISION, ALLOCATABLE :: WORK(:), SCALE(:)
      INTEGER, ALLOCATABLE :: IWORK(:)
      EXTERNAL DGEEVX
      INFO = 0
      IF (N .LT. 0) THEN
         INFO = -5
         RETURN
      END IF
      IF (N .EQ. 0) THEN
         RETURN
      END IF
      ALLOCATE(SCALE(N), WORK(1), IWORK(1))
      LWORK = -1
      CALL DGEEVX(BALANC, JOBVL, JOBVR, SENSE, N, A, LDA, WR, WI,
     $     DUMVL, 1, VR, LDVR, ILO, IHI, SCALE, ABNRM, DUMRC, DUMRV,
     $     WORK, LWORK, IWORK, INFO)
      IF (INFO .NE. 0) THEN
         DEALLOCATE(SCALE, WORK, IWORK)
         RETURN
      END IF
      LWORK = MAX(1, INT(WORK(1)))
      DEALLOCATE(WORK, IWORK)
      ALLOCATE(WORK(LWORK), IWORK(N))
      CALL DGEEVX(BALANC, JOBVL, JOBVR, SENSE, N, A, LDA, WR, WI,
     $     DUMVL, 1, VR, LDVR, ILO, IHI, SCALE, ABNRM, DUMRC, DUMRV,
     $     WORK, LWORK, IWORK, INFO)
      DEALLOCATE(WORK, IWORK, SCALE)
      RETURN
      END
