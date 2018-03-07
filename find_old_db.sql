IF EXISTS (SELECT * FROM sysobjects WHERE  name = 'lll' AND type = 'U') DROP TABLE lll
CREATE TABLE lll (id INT, alias VARCHAR(max), name VARCHAR(max), g varchar(10), d varchar(20), drp varchar(max), dlt varchar(max))

DECLARE @base_name sysname
DECLARE fk_cursor
 CURSOR FOR
   select a.alias from master..listdb a inner join master..LISTSERVER b on a.SERVERID=b.ID inner join sys.databases x on x.name = a.alias where b.NAME='AN' --по списку баз для AN существующие
 OPEN fk_cursor
 FETCH NEXT FROM fk_cursor INTO @base_name
 WHILE (@@FETCH_STATUS =0)
 BEGIN
 BEGIN TRY
   EXEC('use ['+@base_name+']; if exists (select * from sysobjects where name = ''F2'' and type = ''U'' )
         begin
;with tmp as
(SELECT top 1 change_date d, @@SERVERNAME servername, db_name() dbname from protocol where work_id=414 order by change_date desc)                                          ------что ищем
Insert INTO master..lll (id, alias, name, g, d, drp, dlt)
select a.id,a.alias,a.name,isnull(a.dbGroup,''''),convert(varchar(20),tmp.d,126), ''drop database [''+a.alias+'']'', ''delete from listdb where id='' + convert(varchar(10),a.id) from master..listdb a
inner join master..LISTSERVER b on a.SERVERID=b.ID
inner join tmp on tmp.dbname=a.alias
where tmp.d < DATEADD(dd,-40, GETDATE())
         end
        ')
END TRY
BEGIN CATCH
	select 'ERROR ['+@base_name+']: '+ERROR_MESSAGE() ---ошибки если есть
END CATCH;

   FETCH NEXT FROM fk_cursor INTO @base_name
 END
 CLOSE fk_cursor
 DEALLOCATE fk_cursor

SELECT * FROM master..lll           --результат в послдей таблице
  ORDER BY id asc
DROP TABLE master..lll