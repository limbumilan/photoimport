SELECT distinct
    A.ID,
     A.LASTNAME AS SURNAME, A.FIRSTNAME || ' ' || A.MIDDLENAME  AS NAME,
    (SELECT TYPE FROM EDLVRS.GENDER WHERE ID = A.GENDER_ID) AS GENDER, TO_CHAR (a.dateofbirthad,'DD-MM-YYYY') AS DOB,
    A.CITIZENSHIPNUMBER,
    A.PASSPORTNUMBER,
    A.MOBILENUMBER,
    A.WITNESSFIRSTNAME || ' ' || NVL(A.WITNESSMIDDLENAME,'') || ' ' || A.WITNESSLASTNAME AS WITNESS,
    (SELECT TYPE FROM EDLVRS.BLOODGROUP WHERE ID = A.BLOODGROUP_ID) AS BG,
    (SELECT NAME FROM EDLVRS.VILLAGEMETROCITY WHERE ID = AD.VILLAGEMETROCITY_ID)
      || ' ' || AD.WARDNUMBER AS ADDRESS,
    (SELECT NAME FROM EDLVRS.DISTRICT WHERE ID = AD.DISTRICT_ID) AS DISTRICT,
    
    (select name from edlvrs.licenseissueoffice WHERE ID=ld.licenseissueoffice_id )AS LICENSEOFFICE,LD.LICENSEISSUEOFFICE_ID,

    -- CATEGORY FIXED: AGGREGATED ONLY ONCE
    (SELECT LISTAGG(tcl.type, ', ') WITHIN GROUP (ORDER BY tcl.type)
     FROM edlvrs.licensedetail dl
     JOIN edlvrs.licensecategory cl ON cl.licensedetail_id = dl.id
     JOIN edlvrs.licensecategorytype tcl ON tcl.id = cl.lisccategorytype_id
     WHERE dl.newlicenseno = LD.newlicenseno
    ) AS CATEGORY,

    LD.NEWLICENSENO,
    (select TO_CHAR(MIN(CAST(issuedate AS DATE)), 'DD-MM-YYYY')  from edlvrs.licensedetail where newlicenseno=ld.newlicenseno) as ISSUEDATE,
   TO_CHAR(LD.EXPIRYDATE , 'DD-MM-YYYY')  AS EXPIRYDATE
    

FROM EDLVRS.LICENSEDETAIL LD
JOIN EDLVRS.LICENSE L
    ON LD.LICENSE_ID = L.ID
JOIN EDLVRS.APPLICANT A
    ON L.APPLICANT_ID = A.ID
LEFT JOIN EDLVRS.ADDRESS AD
    ON A.ID = AD.APPLICANT_ID

WHERE LD.NEWLICENSENO IN (

'02-06-01032665'

) 
AND LD.expirydate = ( SELECT MAX(expirydate)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID)
 select  A.id,B.user_id
     FROM EDLVRS.APPLICANT A
     INNER JOIN EDLVRS.LICENSE L
     ON A.ID=L.APPLICANT_ID
     INNER JOIN EDLVRS.LICENSEDETAIL LD
     ON L.ID=LD.LICENSE_ID
     INNER JOIN EDLVRS.DOTM_USER_BIOMETRIC B
     ON LD.ISSUE_AUTHORITY_ID=b.user_id
     
     WHERE A.ID IN (
     8588673

     )
     and b.signature is not null and
     ld.expirydate=(
       SELECT MAX(expirydate)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID)
        
        and ld.issuedate=(
       SELECT MAX(issuedate)
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID)
    =========================================
    #..............................finAL
    =========================================
        
SELECT DISTINCT 
       A.id,
       B.user_id
FROM EDLVRS.APPLICANT A
JOIN EDLVRS.LICENSE L
     ON A.ID = L.APPLICANT_ID
JOIN EDLVRS.LICENSEDETAIL LD
     ON L.ID = LD.LICENSE_ID
JOIN EDLVRS.DOTM_USER_BIOMETRIC B
     ON LD.ISSUE_AUTHORITY_ID = B.user_id
WHERE A.ID = 8588673
  AND B.signature IS NOT NULL
  AND LD.ID = (
        SELECT ID
        FROM EDLVRS.LICENSEDETAIL
        WHERE LICENSE_ID = L.ID
        ORDER BY issuedate DESC
        FETCH FIRST 1 ROW ONLY
      );
        
